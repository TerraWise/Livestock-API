import pytest

from internal.inv_extraction import (
    extract_annual_data,
    extract_merino_pct,
    extract_seasonal_data,
    extract_transaction_data,
)

from tests.conftest import annual_row, make_workbook, seasonal_row


class TestExtractSeasonalData:
    def test_happy_path_sheep_and_beef_rows(self, mock_transaction_glob, transaction_xlsx_factory):
        mock_transaction_glob(transaction_xlsx_factory([]))
        wb = make_workbook(
            {
                "Seasonal Data": [
                    seasonal_row(
                        stock="sheep", stock_id="GroupA", stock_class="breedingEwes",
                        head=(100, 100, 100, 100), head_shorn=100, wool_shorn=400, clean_wool_yield=0.9,
                    ),
                    seasonal_row(
                        stock="beef", stock_id="GroupB", stock_class="cowsGt2",
                        head=(50, 50, 50, 50),
                    ),
                ]
            }
        )
        result = extract_seasonal_data(wb)
        sheep_entry = result["sheep"]["GroupA"]["breedingEwes"]
        assert sheep_entry["autumn"]["head"] == 100
        assert sheep_entry["headShorn"] == 100
        assert sheep_entry["woolShorn"] == 400
        assert sheep_entry["cleanWoolYield"] == 0.9
        assert sheep_entry["headSold"] == 0
        assert sheep_entry["purchases"] == [{"head": 0, "purchaseWeight": 0}]

        beef_entry = result["beef"]["GroupB"]["cowsGt2"]
        assert beef_entry["autumn"]["head"] == 50
        assert "headShorn" not in beef_entry
        assert beef_entry["purchases"] == [{"head": 0, "purchaseWeight": 0, "purchaseSource": "Dairy origin"}]

    def test_stock_name_is_lowercased(self, mock_transaction_glob, transaction_xlsx_factory):
        mock_transaction_glob(transaction_xlsx_factory([]))
        wb = make_workbook({"Seasonal Data": [seasonal_row(stock="SHEEP")]})
        result = extract_seasonal_data(wb)
        assert "sheep" in result
        assert "SHEEP" not in result

    def test_hash_prefixed_row_raises_value_error(self, mock_transaction_glob, transaction_xlsx_factory):
        mock_transaction_glob(transaction_xlsx_factory([]))
        wb = make_workbook({"Seasonal Data": [seasonal_row(stock="#comment")]})
        with pytest.raises(ValueError, match="Invalid data in Seasonal Data sheet at row 2"):
            extract_seasonal_data(wb)

    def test_non_string_row_zero_raises_attribute_error(self):
        # Fails at stock.lower() before the transaction/glob mock would even be needed.
        wb = make_workbook({"Seasonal Data": [seasonal_row(stock=123)]})
        with pytest.raises(AttributeError):
            extract_seasonal_data(wb)

    def test_none_row_zero_stops_entirely_ignoring_later_valid_rows(self):
        wb = make_workbook(
            {
                "Seasonal Data": [
                    seasonal_row(stock=None),
                    seasonal_row(stock="beef", stock_id="GroupB", stock_class="cowsGt2"),
                ]
            }
        )
        assert extract_seasonal_data(wb) == {}


class TestExtractTransactionData:
    def test_no_matching_rows_returns_zero_default_sheep(self, mock_transaction_glob, transaction_xlsx_factory):
        mock_transaction_glob(transaction_xlsx_factory([]))
        result = extract_transaction_data("sheep", "GroupA", "breedingEwes")
        assert result == {
            "headSold": 0,
            "saleWeight": 0,
            "purchases": [{"head": 0, "purchaseWeight": 0}],
        }

    def test_no_matching_rows_returns_zero_default_beef(self, mock_transaction_glob, transaction_xlsx_factory):
        mock_transaction_glob(transaction_xlsx_factory([]))
        result = extract_transaction_data("beef", "GroupB", "cowsGt2")
        assert result == {
            "headSold": 0,
            "saleWeight": 0,
            "purchases": [{"head": 0, "purchaseWeight": 0, "purchaseSource": "Dairy origin"}],
        }

    def test_weighted_average_sale_weight_with_round_numbers(self, mock_transaction_glob, transaction_xlsx_factory):
        rows = [
            {"Stock group": "sheep GroupA", "Stock class": "breedingEwes", "Head": 60,
             "Average liveweight (kg)": 100, "Transaction type": "Sale", "Source": None,
             "Merino sheep purchased (head)": 0},
            {"Stock group": "sheep GroupA", "Stock class": "breedingEwes", "Head": 40,
             "Average liveweight (kg)": 200, "Transaction type": "Sale", "Source": None,
             "Merino sheep purchased (head)": 0},
        ]
        mock_transaction_glob(transaction_xlsx_factory(rows))
        result = extract_transaction_data("sheep", "GroupA", "breedingEwes")
        assert result["headSold"] == 100
        assert result["saleWeight"] == 140
        assert result["purchases"] == [{"head": 0, "purchaseWeight": 0}]

    def test_all_zero_head_rows_default_sale_weight_to_zero(self, mock_transaction_glob, transaction_xlsx_factory):
        # Regression test for the zero-head-sold guard: a matching row (so
        # filtered_df isn't empty) whose Head values sum to zero must not
        # divide by zero -- saleWeight defaults to 0 instead of NaN.
        rows = [
            {"Stock group": "sheep GroupA", "Stock class": "breedingEwes", "Head": 0,
             "Average liveweight (kg)": 100, "Transaction type": "Sale", "Source": None,
             "Merino sheep purchased (head)": 0},
        ]
        mock_transaction_glob(transaction_xlsx_factory(rows))
        result = extract_transaction_data("sheep", "GroupA", "breedingEwes")
        assert result["headSold"] == 0
        assert result["saleWeight"] == 0

    def test_multiple_beef_purchase_rows_each_get_own_source(self, mock_transaction_glob, transaction_xlsx_factory):
        rows = [
            {"Stock group": "beef GroupB", "Stock class": "cowsGt2", "Head": 10,
             "Average liveweight (kg)": 300, "Transaction type": "Purchase", "Source": "sw WA",
             "Merino sheep purchased (head)": 0},
            {"Stock group": "beef GroupB", "Stock class": "cowsGt2", "Head": 20,
             "Average liveweight (kg)": 450, "Transaction type": "Purchase", "Source": "WA pastoral",
             "Merino sheep purchased (head)": 0},
        ]
        mock_transaction_glob(transaction_xlsx_factory(rows))
        result = extract_transaction_data("beef", "GroupB", "cowsGt2")
        assert result["headSold"] == 30
        assert result["saleWeight"] == 400
        assert result["purchases"] == [
            {"head": 10, "purchaseWeight": 300, "purchaseSource": "sw WA"},
            {"head": 20, "purchaseWeight": 450, "purchaseSource": "WA pastoral"},
        ]

    def test_sheep_purchase_rows_never_carry_a_purchase_source_key(self, mock_transaction_glob, transaction_xlsx_factory):
        rows = [
            {"Stock group": "sheep GroupA", "Stock class": "breedingEwes", "Head": 5,
             "Average liveweight (kg)": 40, "Transaction type": "Purchase", "Source": "sw WA",
             "Merino sheep purchased (head)": 5},
        ]
        mock_transaction_glob(transaction_xlsx_factory(rows))
        result = extract_transaction_data("sheep", "GroupA", "breedingEwes")
        assert result["purchases"] == [{"head": 5, "purchaseWeight": 40}]


class TestExtractMerinoPct:
    def test_no_purchase_rows_defaults_to_zero(self, mock_transaction_glob, transaction_xlsx_factory):
        mock_transaction_glob(transaction_xlsx_factory([]))
        json_data = {"sheep": [{"id": "GroupA"}]}
        result = extract_merino_pct(json_data, "sheep", 0)
        assert result["sheep"][0]["merinoPercent"] == 0

    def test_weighted_computation_with_round_numbers(self, mock_transaction_glob, transaction_xlsx_factory):
        rows = [
            {"Stock group": "sheep GroupA", "Stock class": "breedingEwes", "Head": 80,
             "Average liveweight (kg)": 40, "Transaction type": "Purchase", "Source": None,
             "Merino sheep purchased (head)": 80},
            {"Stock group": "sheep GroupA", "Stock class": "eweLambs", "Head": 20,
             "Average liveweight (kg)": 30, "Transaction type": "Purchase", "Source": None,
             "Merino sheep purchased (head)": 0},
        ]
        mock_transaction_glob(transaction_xlsx_factory(rows))
        json_data = {"sheep": [{"id": "GroupA"}]}
        result = extract_merino_pct(json_data, "sheep", 0)
        assert result["sheep"][0]["merinoPercent"] == 0.8

    def test_all_zero_head_purchase_rows_default_to_zero(self, mock_transaction_glob, transaction_xlsx_factory):
        # Regression test for the zero-head-sold guard: a matching purchase
        # row whose Head sums to zero must not divide by zero -- merinoPercent
        # defaults to 0 instead of NaN.
        rows = [
            {"Stock group": "sheep GroupA", "Stock class": "breedingEwes", "Head": 0,
             "Average liveweight (kg)": 40, "Transaction type": "Purchase", "Source": None,
             "Merino sheep purchased (head)": 0},
        ]
        mock_transaction_glob(transaction_xlsx_factory(rows))
        json_data = {"sheep": [{"id": "GroupA"}]}
        result = extract_merino_pct(json_data, "sheep", 0)
        assert result["sheep"][0]["merinoPercent"] == 0


class TestExtractAnnualData:
    def test_ids_route_to_correct_group_and_limestone_no_longer_collides_with_id(self, beef_factory):
        # Regression test for the row[3]->row[2] fix: distinct sentinel values at
        # the ID column and the limestone column must not be confused, and each
        # row's data must land in the group matching its own ID.
        livestock = beef_factory(groups=2, ids=["GroupA", "GroupB"])
        rows = [
            annual_row(stock="beef", id_value="GroupA", limestone=111),
            annual_row(stock="beef", id_value="GroupB", limestone=222),
        ]
        wb = make_workbook({"Annual Data": rows})
        result = extract_annual_data(wb, livestock)
        assert result["beef"][0]["limestone"] == 111
        assert result["beef"][1]["limestone"] == 222

    def test_unmatched_id_falls_back_to_group_zero(self, beef_factory):
        livestock = beef_factory(groups=2, ids=["GroupA", "GroupB"])
        rows = [annual_row(stock="beef", id_value="Stray", limestone=999)]
        wb = make_workbook({"Annual Data": rows})
        result = extract_annual_data(wb, livestock)
        assert result["beef"][0]["limestone"] == 999
        # GroupB has no matching Annual Data row, so it keeps the zeroed default
        # rather than being left without a "limestone" key at all.
        assert result["beef"][1]["limestone"] == 0

    def test_sheep_only_seasonal_lambing_and_merino_percent(
        self, sheep_factory, mock_transaction_glob, transaction_xlsx_factory
    ):
        mock_transaction_glob(transaction_xlsx_factory([]))
        livestock = sheep_factory(groups=1, ids=["GroupA"])
        rows = [annual_row(id_value="GroupA", seasonal_lambing=(1, 2, 3, 4))]
        wb = make_workbook({"Annual Data": rows})
        result = extract_annual_data(wb, livestock)
        assert result["sheep"][0]["seasonalLambing"] == {
            "autumn": 1, "winter": 2, "spring": 3, "summer": 4,
        }
        assert result["sheep"][0]["merinoPercent"] == 0

    def test_beef_has_no_seasonal_lambing_or_merino_percent(self, beef_factory):
        livestock = beef_factory(groups=1, ids=["GroupA"])
        rows = [annual_row(stock="beef", id_value="GroupA")]
        wb = make_workbook({"Annual Data": rows})
        result = extract_annual_data(wb, livestock)
        assert "seasonalLambing" not in result["beef"][0]
        assert "merinoPercent" not in result["beef"][0]

    def test_zero_matching_rows_still_gets_merino_percent_default(
        self, sheep_factory, mock_transaction_glob, transaction_xlsx_factory
    ):
        # Regression test for the log/error.json 422 bug ("sheep.0.merinoPercent:
        # expected number, received undefined"): merinoPercent is now computed
        # once per group after the row loop (it depends only on the Transaction
        # sheet, not on any Annual Data row), so every sheep group gets a value
        # even when it has zero matching Annual Data rows.
        mock_transaction_glob(transaction_xlsx_factory([]))
        livestock = sheep_factory(groups=2, ids=["GroupA", "GroupB"])
        wb = make_workbook({"Annual Data": []})
        result = extract_annual_data(wb, livestock)
        assert result["sheep"][0]["merinoPercent"] == 0
        assert result["sheep"][1]["merinoPercent"] == 0
