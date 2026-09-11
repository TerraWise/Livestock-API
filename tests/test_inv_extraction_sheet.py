import pandas as pd
import pytest

from internal.inv_extraction import (
    extract_annual_data,
    extract_merino_pct,
    extract_seasonal_data,
    extract_transaction_data,
)

from tests.conftest import (
    CATTLE_ENTERPRISE,
    SHEEP_ENTERPRISE,
    annual_row,
    breed_row,
    seasonal_row,
    transaction_row,
)

# Group ids in the Transaction tests below are deliberately all-lowercase
# ("groupa", not "GroupA"). Neither Transaction lookup matches when the id needs
# case folding, so lowercase ids are what let these tests actually exercise the
# filtering, the weighted average and the purchase-source branches -- the code
# the refactor touches.
#
# The real sheet's Stock group values are Title case ("Sheep Merino"), which
# neither lookup handles. That is a source bug, reported separately, not
# something these tests assert either way.


class TestExtractSeasonalData:
    """extract_seasonal_data(species) resolves its own sheet via glob now, so
    every case here needs mock_transaction_glob -- there is no more path that
    reaches row data before the sheet is read (see the two tests below that
    used to skip the mock).
    """

    def test_happy_path_sheep_and_beef_rows(
        self, mock_transaction_glob, input_xlsx_factory
    ):
        # One call per species: extract_seasonal_data now filters by the
        # species argument, so a sheep call never sees the beef row and vice
        # versa -- unlike the old workbook-wide pass.
        mock_transaction_glob(
            input_xlsx_factory(
                seasonal=[
                    seasonal_row(
                        stock="sheep",
                        stock_id="GroupA",
                        stock_class="breedingEwes",
                        head=(100, 100, 100, 100),
                        head_shorn=100,
                        wool_shorn=400,
                        clean_wool_yield=0.9,
                    ),
                    seasonal_row(
                        stock="beef",
                        stock_id="GroupB",
                        stock_class="cowsGt2",
                        head=(50, 50, 50, 50),
                    ),
                ]
            )
        )

        sheep_result = extract_seasonal_data("sheep")
        sheep_entry = sheep_result["sheep"]["GroupA"]["breedingEwes"]
        assert sheep_entry["autumn"]["head"] == 100
        assert sheep_entry["headShorn"] == 100
        assert sheep_entry["woolShorn"] == 400
        assert sheep_entry["cleanWoolYield"] == 0.9
        assert sheep_entry["headSold"] == 0
        assert sheep_entry["purchases"] == [{"head": 0, "purchaseWeight": 0}]
        assert "beef" not in sheep_result

        beef_result = extract_seasonal_data("beef")
        beef_entry = beef_result["beef"]["GroupB"]["cowsGt2"]
        assert beef_entry["autumn"]["head"] == 50
        assert "headShorn" not in beef_entry
        assert beef_entry["purchases"] == [
            {"head": 0, "purchaseWeight": 0, "purchaseSource": "Dairy origin"}
        ]
        assert "sheep" not in beef_result

    def test_stock_name_is_lowercased(
        self, mock_transaction_glob, input_xlsx_factory
    ):
        mock_transaction_glob(
            input_xlsx_factory(seasonal=[seasonal_row(stock="SHEEP")])
        )
        result = extract_seasonal_data("sheep")
        assert "sheep" in result
        assert "SHEEP" not in result

    def test_unmatched_stock_category_is_skipped_not_validated(
        self, mock_transaction_glob, input_xlsx_factory
    ):
        # The old "#"-prefixed-value ValueError check is gone: a Stock category
        # that doesn't match `species` is now just skipped like any other
        # mismatch, string or not.
        mock_transaction_glob(
            input_xlsx_factory(seasonal=[seasonal_row(stock="#comment")])
        )
        assert extract_seasonal_data("sheep") == {}

    def test_non_string_row_zero_raises_attribute_error(
        self, mock_transaction_glob, input_xlsx_factory
    ):
        mock_transaction_glob(
            input_xlsx_factory(seasonal=[seasonal_row(stock=123)])
        )
        with pytest.raises(AttributeError):
            extract_seasonal_data("sheep")

    def test_none_row_zero_raises_value_error_immediately(
        self, mock_transaction_glob, input_xlsx_factory
    ):
        # A missing Stock category on any row raises straight away now -- there
        # is no more "stop silently and keep whatever was collected so far"
        # fallback, so the later valid row is never reached either.
        mock_transaction_glob(
            input_xlsx_factory(
                seasonal=[
                    seasonal_row(stock=None),
                    seasonal_row(
                        stock="beef", stock_id="GroupB", stock_class="cowsGt2"
                    ),
                ]
            )
        )
        with pytest.raises(
            ValueError, match="Missing value in seasonal data row: 2"
        ):
            extract_seasonal_data("beef")


class TestExtractTransactionData:
    def test_no_matching_rows_returns_zero_default_sheep(
        self, mock_transaction_glob, transaction_xlsx_factory
    ):
        mock_transaction_glob(transaction_xlsx_factory([]))
        result = extract_transaction_data("sheep", "groupa", "breedingEwes")
        assert result == {
            "headSold": 0,
            "saleWeight": 0,
            "purchases": [{"head": 0, "purchaseWeight": 0}],
        }

    def test_no_matching_rows_returns_zero_default_beef(
        self, mock_transaction_glob, transaction_xlsx_factory
    ):
        mock_transaction_glob(transaction_xlsx_factory([]))
        result = extract_transaction_data("beef", "groupb", "cowsGt2")
        assert result == {
            "headSold": 0,
            "saleWeight": 0,
            "purchases": [
                {"head": 0, "purchaseWeight": 0, "purchaseSource": "Dairy origin"}
            ],
        }

    def test_weighted_average_sale_weight_with_round_numbers(
        self, mock_transaction_glob, transaction_xlsx_factory
    ):
        rows = [
            transaction_row(quantity=60, liveweight=100),
            transaction_row(quantity=40, liveweight=200),
        ]
        mock_transaction_glob(transaction_xlsx_factory(rows))
        result = extract_transaction_data("sheep", "groupa", "breedingEwes")
        assert result["headSold"] == 100
        assert result["saleWeight"] == 140
        assert result["purchases"] == [{"head": 0, "purchaseWeight": 0}]

    def test_all_zero_head_rows_default_sale_weight_to_zero(
        self, mock_transaction_glob, transaction_xlsx_factory
    ):
        # Regression test for the zero-head-sold guard: a matching row (so
        # filtered_df isn't empty) whose Quantity values sum to zero must not
        # divide by zero -- saleWeight defaults to 0 instead of NaN.
        #
        # The asserted values coincide with the no-match defaults, so the
        # lowercase group id is what makes this test meaningful: it guarantees
        # the row really matches and the guard really runs.
        rows = [transaction_row(quantity=0, liveweight=100)]
        mock_transaction_glob(transaction_xlsx_factory(rows))
        result = extract_transaction_data("sheep", "groupa", "breedingEwes")
        assert result["headSold"] == 0
        assert result["saleWeight"] == 0

    def test_multiple_beef_purchase_rows_each_get_own_source(
        self, mock_transaction_glob, transaction_xlsx_factory
    ):
        rows = [
            transaction_row(
                stock_group="beef groupb",
                code_name="cowsGt2",
                transaction_type="Purchase",
                quantity=10,
                liveweight=300,
                source="sw WA",
            ),
            transaction_row(
                stock_group="beef groupb",
                code_name="cowsGt2",
                transaction_type="Purchase",
                quantity=20,
                liveweight=450,
                source="WA pastoral",
            ),
        ]
        mock_transaction_glob(transaction_xlsx_factory(rows))
        result = extract_transaction_data("beef", "groupb", "cowsGt2")
        # headSold/saleWeight are now filtered to Transaction type == "Sale"
        # only, so these two Purchase rows contribute nothing to either -- the
        # empty-sales-match guard (safe_ratio) is what keeps saleWeight at 0
        # instead of dividing by a zero Quantity sum.
        assert result["headSold"] == 0
        assert result["saleWeight"] == 0
        assert result["purchases"] == [
            {"head": 10, "purchaseWeight": 300, "purchaseSource": "sw WA"},
            {"head": 20, "purchaseWeight": 450, "purchaseSource": "WA pastoral"},
        ]

    def test_sheep_purchase_rows_never_carry_a_purchase_source_key(
        self, mock_transaction_glob, transaction_xlsx_factory
    ):
        rows = [
            transaction_row(
                transaction_type="Purchase",
                quantity=5,
                liveweight=40,
                source="sw WA",
                merino_head=5,
            )
        ]
        mock_transaction_glob(transaction_xlsx_factory(rows))
        result = extract_transaction_data("sheep", "groupa", "breedingEwes")
        assert result["purchases"] == [{"head": 5, "purchaseWeight": 40}]


class TestExtractMerinoPct:
    def test_no_purchase_rows_defaults_to_zero(
        self, mock_transaction_glob, transaction_xlsx_factory
    ):
        mock_transaction_glob(transaction_xlsx_factory([]))
        json_data = {"sheep": [{"id": "groupa"}]}
        result = extract_merino_pct(json_data, "sheep", 0)
        assert result["sheep"][0]["merinoPercent"] == 0

    def test_weighted_computation_with_round_numbers(
        self, mock_transaction_glob, transaction_xlsx_factory
    ):
        rows = [
            transaction_row(
                transaction_type="Purchase",
                quantity=80,
                liveweight=40,
                merino_head=80,
            ),
            transaction_row(
                code_name="eweLambs",
                transaction_type="Purchase",
                quantity=20,
                liveweight=30,
                merino_head=0,
            ),
        ]
        mock_transaction_glob(transaction_xlsx_factory(rows))
        json_data = {"sheep": [{"id": "groupa"}]}
        result = extract_merino_pct(json_data, "sheep", 0)
        assert result["sheep"][0]["merinoPercent"] == 0.8

    def test_all_zero_head_purchase_rows_default_to_zero(
        self, mock_transaction_glob, transaction_xlsx_factory
    ):
        # Divide-by-zero guard, same shape as its extract_transaction_data
        # counterpart above: the lowercase id is what makes the row match, so
        # the guard is genuinely exercised rather than short-circuited.
        rows = [transaction_row(transaction_type="Purchase", quantity=0, liveweight=40)]
        mock_transaction_glob(transaction_xlsx_factory(rows))
        json_data = {"sheep": [{"id": "groupa"}]}
        result = extract_merino_pct(json_data, "sheep", 0)
        assert result["sheep"][0]["merinoPercent"] == 0


class TestExtractAnnualData:
    """extract_annual_data(livestock) resolves "Annual Data - Enterprise"
    itself via glob now -- every case needs mock_transaction_glob and an
    input_xlsx_factory(annual=[...]) sheet instead of a workbook argument.
    """

    def test_enterprise_row_lands_on_its_own_group(
        self, beef_factory, mock_transaction_glob, input_xlsx_factory
    ):
        # "Annual Data - Enterprise" carries one row per enterprise, matched
        # against livestock.ids by "Stock category". Annual inputs are
        # collected per enterprise, so a breed group has no row of its own and
        # keeps the zeroed ANNUAL_DATA_DEFAULTS rather than being left without
        # the key.
        mock_transaction_glob(
            input_xlsx_factory(
                annual=[annual_row(stock_cat=CATTLE_ENTERPRISE, limestone=111)]
            )
        )
        livestock = beef_factory(groups=2, ids=[CATTLE_ENTERPRISE, "Angus"])
        result = extract_annual_data(livestock)
        assert result["beef"][0]["limestone"] == 111
        assert result["beef"][1]["limestone"] == 0

    def test_unmatched_enterprise_row_is_skipped(
        self, beef_factory, mock_transaction_glob, input_xlsx_factory
    ):
        # A row whose "Stock category" matches no group is skipped outright. It
        # used to fall back to group 0, which silently misattributed one
        # enterprise's lime and fuel to another; skipping is the correct
        # behaviour and this test pins it so the old fallback cannot come back.
        mock_transaction_glob(
            input_xlsx_factory(annual=[annual_row(stock_cat="Stray", limestone=999)])
        )
        livestock = beef_factory(groups=2, ids=[CATTLE_ENTERPRISE, "Angus"])
        result = extract_annual_data(livestock)
        assert result["beef"][0]["limestone"] == 0
        assert result["beef"][1]["limestone"] == 0

    def test_sheep_breed_group_gets_rates_from_the_breed_sheet(
        self, sheep_factory, mock_transaction_glob, input_xlsx_factory
    ):
        # ewesLambing and seasonalLambing read different breed-sheet columns
        # (a deliberate AIA-shape split, not a shared column -- see
        # TestExtractLambingCalvingRate in test_inv_extraction.py), so
        # `lambing=` feeds ewesLambing and `marking=` feeds seasonalLambing.
        # Both are looked up by column NAME, so the sheet's physical
        # Autumn/Spring/Summer/Winter order maps correctly onto SEASONS'
        # autumn/winter/spring/summer output order.
        mock_transaction_glob(
            input_xlsx_factory(
                breeds=[
                    breed_row(
                        stock_group="Sheep Merino",
                        lambing=(11, 22, 33, 44),
                        marking=(1, 2, 3, 4),
                    )
                ],
                annual=[annual_row()],
            )
        )
        livestock = sheep_factory(groups=2, ids=[SHEEP_ENTERPRISE, "Merino"])
        result = extract_annual_data(livestock)

        merino = result["sheep"][1]
        assert merino["ewesLambing"] == {
            "autumn": 11,
            "winter": 44,
            "spring": 22,
            "summer": 33,
        }
        assert merino["seasonalLambing"] == {
            "autumn": 1,
            "winter": 4,
            "spring": 2,
            "summer": 3,
        }
        assert merino["merinoPercent"] == 0

        # Group 0 looks itself up as "Sheep Sheep for allocation", which the
        # breed sheet never contains, so it always reads zeros.
        assert result["sheep"][0]["seasonalLambing"] == {
            "autumn": 0,
            "winter": 0,
            "spring": 0,
            "summer": 0,
        }

    def test_beef_has_no_seasonal_lambing_or_merino_percent(
        self, beef_factory, mock_transaction_glob, input_xlsx_factory
    ):
        # seasonalLambing and merinoPercent are sheep-only; the gate lives in
        # extract_annual_data, not in the rate extractors themselves.
        mock_transaction_glob(
            input_xlsx_factory(annual=[annual_row(stock_cat=CATTLE_ENTERPRISE)])
        )
        livestock = beef_factory(groups=1, ids=[CATTLE_ENTERPRISE])
        result = extract_annual_data(livestock)
        assert "seasonalLambing" not in result["beef"][0]
        assert "merinoPercent" not in result["beef"][0]
        assert "cowsCalving" in result["beef"][0]

    def test_zero_matching_rows_still_gets_merino_percent_default(
        self, sheep_factory, mock_transaction_glob, input_xlsx_factory
    ):
        # Regression test for the log/error.json 422 bug ("sheep.0.merinoPercent:
        # expected number, received undefined"): merinoPercent is computed once
        # per group after the row loop (it depends only on the Transaction sheet,
        # not on any Annual Data row), so every sheep group gets a value even
        # when it has zero matching Annual Data rows.
        mock_transaction_glob(input_xlsx_factory())
        livestock = sheep_factory(groups=2, ids=[SHEEP_ENTERPRISE, "Merino"])
        result = extract_annual_data(livestock)
        assert result["sheep"][0]["merinoPercent"] == 0
        assert result["sheep"][1]["merinoPercent"] == 0


class TestSheetCache:
    """The memoised loader replaced four copies of glob + read_excel.

    These pin the two properties that make the memoisation safe, so neither the
    per-call re-parsing nor a stale-frame bug can return unnoticed.
    """

    def test_a_sheet_is_parsed_once_however_many_callers_ask(
        self, mock_transaction_glob, transaction_xlsx_factory, monkeypatch
    ):
        mock_transaction_glob(transaction_xlsx_factory([]))
        seen = []
        real = pd.read_excel

        def counting(path, sheet, *args, **kwargs):
            seen.append(sheet)
            return real(path, sheet, *args, **kwargs)

        monkeypatch.setattr("internal.inv_extraction.pd.read_excel", counting)
        for _ in range(5):
            extract_transaction_data("sheep", "groupa", "breedingEwes")
        assert seen == ["Transaction"]

    def test_a_different_workbook_is_never_served_from_cache(
        self, mock_transaction_glob, transaction_xlsx_factory
    ):
        # The cache key includes the resolved path, so pointing glob at a new
        # file must re-read rather than reuse the first frame.
        mock_transaction_glob(
            transaction_xlsx_factory([transaction_row(quantity=60, liveweight=100)])
        )
        first = extract_transaction_data("sheep", "groupa", "breedingEwes")
        assert first["headSold"] == 60

        mock_transaction_glob(transaction_xlsx_factory([]))
        second = extract_transaction_data("sheep", "groupa", "breedingEwes")
        assert second["headSold"] == 0
