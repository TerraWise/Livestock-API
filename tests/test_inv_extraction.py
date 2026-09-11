import pandas as pd
import pytest

from internal.inv_extraction import (
    build_purchase_entry,
    extract_column_data,
    extract_electricity_data,
    extract_feed_data,
    extract_fertiliser_data,
    extract_lambing_calving_rate,
    extract_seasonal_row_data,
    extract_breed_rate,
    extract_wool_row_data,
)
from internal.constant import (
    ANNUAL_NESTED_COLUMNS,
    ANNUAL_SCALAR_COLUMNS,
    OTHER_N_FERTILISERS,
    SEASONS,
)

from tests.conftest import annual_row, breed_row, seasonal_row

# Valid "Purchase source" values, per the data-validation list configured in the
# real Excel workbook (not enforced anywhere in the Python code itself).
VALID_PURCHASE_SOURCES = [
    "Dairy origin",
    "nth/sth/central QLD",
    "nth/sth NSW/VIC/sth SA",
    "NSW/SA pastoral zone",
    "sw WA",
    "WA pastoral",
    "TAS",
    "NT",
]

# "Electricity source" is a two-value data-validation dropdown in the real
# workbook: always exactly "State Grid" or "Renewable" -- no other casing or
# string reaches this code from real data entry.
VALID_ELECTRICITY_SOURCES = ["State Grid", "Renewable"]


def test_other_n_fertilisers_exact_list():
    assert OTHER_N_FERTILISERS == {
        "Monoammonium phosphate (MAP)": "MAP",
        "Diammonium Phosphate (DAP)": "DAP",
        "Urea-Ammonium Nitrate (UAN)": "UAN",
        "Ammonium Nitrate (AN)": "AN",
        "Calcium Ammonium Nitrate (CAN)": "CAN",
        "Triple Superphosphate (TSP)": "TSP",
        "Super Potash 1:1": "Super potash 1:1",
        "Super Potash 2:1": "Super potash 2:1",
        "Super Potash 3:1": "Super potash 3:1",
        "Super Potash 4:1": "Super potash 4:1",
        "Super Potash 5:1": "Super potash 5:1",
        "Muriate of Potash": "MOP",
        "Sulphate of Potash": "SOP",
        "Sulphate of Ammonia": "SOA",
    }


class TestExtractSeasonalRowData:
    def test_happy_path_all_fields(self):
        row = seasonal_row(
            head=(10, 20, 30, 40),
            liveweight=(1, 2, 3, 4),
            liveweight_gain=(0.1, 0.2, 0.3, 0.4),
            crude_protein=(11, 12, 13, 14),
            dry_matter_digestibility=(21, 22, 23, 24),
            feed_availability=(31, 32, 33, 34),
        )
        result = extract_seasonal_row_data(row)
        assert result == {
            "autumn": {
                "head": 10,
                "liveweight": 1,
                "liveweightGain": 0.1,
                "crudeProtein": 11,
                "dryMatterDigestibility": 21,
                "feedAvailability": 31,
            },
            "winter": {
                "head": 20,
                "liveweight": 2,
                "liveweightGain": 0.2,
                "crudeProtein": 12,
                "dryMatterDigestibility": 22,
                "feedAvailability": 32,
            },
            "spring": {
                "head": 30,
                "liveweight": 3,
                "liveweightGain": 0.3,
                "crudeProtein": 13,
                "dryMatterDigestibility": 23,
                "feedAvailability": 33,
            },
            "summer": {
                "head": 40,
                "liveweight": 4,
                "liveweightGain": 0.4,
                "crudeProtein": 14,
                "dryMatterDigestibility": 24,
                "feedAvailability": 34,
            },
        }

    def test_optional_fields_omitted_entirely_when_none(self):
        row = seasonal_row(head=(10, 20, 30, 40))
        result = extract_seasonal_row_data(row)
        for season in SEASONS:
            assert set(result[season].keys()) == {
                "head",
                "liveweight",
                "liveweightGain",
            }

    def test_partial_optional_fields_are_independent_per_season(self):
        row = seasonal_row(crude_protein=(5, None, None, None))
        result = extract_seasonal_row_data(row)
        assert result["autumn"]["crudeProtein"] == 5
        assert "crudeProtein" not in result["winter"]
        assert "crudeProtein" not in result["spring"]
        assert "crudeProtein" not in result["summer"]


class TestExtractWoolRowData:
    def test_happy_path(self):
        row = seasonal_row(head_shorn=100, wool_shorn=400, clean_wool_yield=0.85)
        assert extract_wool_row_data(row) == {
            "headShorn": 100,
            "woolShorn": 400,
            "cleanWoolYield": 0.85,
        }

    def test_all_fields_pass_raw_none_through_unguarded(self):
        # No field is defaulted here: extract_wool_row_data reads all three
        # straight off the row, None included.
        row = seasonal_row(head_shorn=None, wool_shorn=None, clean_wool_yield=None)
        assert extract_wool_row_data(row) == {
            "headShorn": None,
            "woolShorn": None,
            "cleanWoolYield": None,
        }


class TestBuildPurchaseEntry:
    def test_beef_explicit_source(self):
        assert build_purchase_entry("beef", 10, 200, "sw WA") == {
            "head": 10,
            "purchaseWeight": 200,
            "purchaseSource": "sw WA",
        }

    def test_beef_default_source_is_dairy_origin(self):
        assert build_purchase_entry("beef", 0, 0) == {
            "head": 0,
            "purchaseWeight": 0,
            "purchaseSource": "Dairy origin",
        }

    def test_sheep_source_argument_is_silently_dropped(self):
        assert build_purchase_entry("sheep", 5, 50, "sw WA") == {
            "head": 5,
            "purchaseWeight": 50,
        }


class TestExtractColumnData:
    """The table-driven pass over ANNUAL_SCALAR_COLUMNS / ANNUAL_NESTED_COLUMNS.

    Replaces the per-concern lime / fuel / supplementation / chemical tests.
    Driving the assertions off the tables themselves means a new column is
    covered the moment it is added, and no column can be silently dropped.
    """

    # Every column maps to its own name, so entry[key] == column proves
    # extract_column_data read that exact column -- not a neighbour, not a
    # stale index -- without needing to track a separate position per field.
    SENTINEL_ROW = pd.Series(
        {
            col: col
            for col in (
                list(ANNUAL_SCALAR_COLUMNS.values())
                + [c for cols in ANNUAL_NESTED_COLUMNS.values() for c in cols.values()]
            )
        }
    )

    @pytest.mark.parametrize("key,column", sorted(ANNUAL_SCALAR_COLUMNS.items()))
    def test_each_scalar_field_reads_its_own_column(self, key, column):
        result = extract_column_data({"beef": [{}]}, self.SENTINEL_ROW, "beef", 0)
        assert result["beef"][0][key] == column

    @pytest.mark.parametrize("key,columns", sorted(ANNUAL_NESTED_COLUMNS.items()))
    def test_each_nested_block_reads_its_own_columns(self, key, columns):
        result = extract_column_data({"beef": [{}]}, self.SENTINEL_ROW, "beef", 0)
        assert result["beef"][0][key] == columns

    def test_reads_a_realistic_row(self):
        row = annual_row(
            limestone=250,
            limestone_fraction=0.75,
            diesel=111,
            petrol=222,
            lpg=333,
            mineral=(1, 2, 3, 4, 5, 6),
            herbicide=7,
            herbicide_other=8,
        )
        entry = extract_column_data({"beef": [{}]}, row, "beef", 0)["beef"][0]
        assert entry["limestone"] == 250
        assert entry["limestoneFraction"] == 0.75
        assert entry["diesel"] == 111
        assert entry["petrol"] == 222
        assert entry["lpg"] == 333
        assert entry["herbicide"] == 7
        assert entry["herbicideOther"] == 8
        assert entry["mineralSupplementation"] == {
            "mineralBlock": 1,
            "mineralBlockUrea": 2,
            "weanerBlock": 3,
            "weanerBlockUrea": 4,
            "drySeasonMix": 5,
            "drySeasonMixUrea": 6,
        }


class TestExtractFertiliserData:
    def test_exact_column_mapping(self):
        json_data = {"beef": [{}]}
        row = annual_row(
            single_super=11,
            pasture_dryland=22,
            other_ferts=tuple(range(100, 114)),
        )
        result = extract_fertiliser_data(json_data, row, "beef", 0)
        fert = result["beef"][0]["fertiliser"]
        assert fert["singleSuperphosphate"] == 11
        assert fert["pastureDryland"] == 22
        assert fert["pastureIrrigated"] == 0
        # cropsDryland is hardcoded to 0: the sheet's "Urea Crop" column (index
        # 5) is not read by anything, and no irrigated columns exist at all.
        assert fert["cropsDryland"] == 0
        assert fert["cropsIrrigated"] == 0
        assert len(fert["otherFertilisers"]) == 14
        other_fertiliser_names = list(OTHER_N_FERTILISERS)
        for idx, entry in enumerate(fert["otherFertilisers"]):
            assert entry["otherDryland"] == 100 + idx
            assert entry["otherIrrigated"] == 0
            assert entry["otherType"] == other_fertiliser_names[idx]


class TestExtractElectricityData:
    # "Electricity source" is a two-value Excel dropdown (State Grid / Renewable),
    # so only those two inputs are exercised here.
    def test_state_grid_includes_renewable_field(self):
        json_data = {"beef": [{}]}
        row = annual_row(
            electricity_source="State Grid",
            electricity_renewable=500,
            electricity_use=5000,
        )
        result = extract_electricity_data(json_data, row, "beef", 0)
        entry = result["beef"][0]
        assert entry["electricitySource"] == "State Grid"
        assert entry["electricityRenewable"] == 500
        assert entry["electricityUse"] == 5000

    def test_renewable_omits_field_entirely(self):
        json_data = {"beef": [{}]}
        row = annual_row(electricity_source="Renewable", electricity_renewable=500)
        result = extract_electricity_data(json_data, row, "beef", 0)
        assert "electricityRenewable" not in result["beef"][0]


class TestExtractFeedData:
    def test_beef_includes_cottonseed_feed(self):
        json_data = {"beef": [{}]}
        row = annual_row(grain_feed=10, hay_feed=20, cottonseed_feed=30)
        result = extract_feed_data(json_data, row, "beef", 0)
        entry = result["beef"][0]
        assert entry["grainFeed"] == 10
        assert entry["hayFeed"] == 20
        assert entry["cottonseedFeed"] == 30

    def test_sheep_excludes_cottonseed_feed(self):
        json_data = {"sheep": [{}]}
        row = annual_row(grain_feed=10, hay_feed=20, cottonseed_feed=30)
        result = extract_feed_data(json_data, row, "sheep", 0)
        assert "cottonseedFeed" not in result["sheep"][0]


class TestExtractLambingCalvingRate:
    """ewesLambing and cowsCalving read different sheet columns.

    cowsCalving reads "Lambs/Calfs marking Rate {Season}". ewesLambing reads
    "Proportion of ewes lambing/cows calving {Season}" instead -- a deliberate
    split, not a shared column, kept this way as a workaround for how the AIA
    endpoint expects sheep reproduction data shaped.

    The lookup is by column name, so the sheet's physical Autumn/Spring/Summer/
    Winter order maps correctly onto SEASONS' autumn/winter/spring/summer
    output order -- hence the transposed expectations below.
    """

    def test_sheep_uses_ewes_lambing_key(
        self, mock_transaction_glob, input_xlsx_factory
    ):
        mock_transaction_glob(
            input_xlsx_factory(
                breeds=[breed_row(stock_group="Sheep Merino", lambing=(11, 22, 33, 44))]
            )
        )
        assert extract_lambing_calving_rate("Sheep Merino") == {
            "ewesLambing": {
                "autumn": 11,
                "winter": 44,
                "spring": 22,
                "summer": 33,
            }
        }

    def test_beef_uses_cows_calving_key(
        self, mock_transaction_glob, input_xlsx_factory
    ):
        # The output key is chosen by looking for "sheep" in the stock group
        # string, so a beef group gets cowsCalving.
        mock_transaction_glob(
            input_xlsx_factory(
                breeds=[breed_row(stock_group="Beef Angus", marking=(11, 22, 33, 44))]
            )
        )
        assert extract_lambing_calving_rate("Beef Angus") == {
            "cowsCalving": {
                "autumn": 11,
                "winter": 44,
                "spring": 22,
                "summer": 33,
            }
        }

    def test_stock_group_absent_from_the_sheet_yields_zeros(
        self, mock_transaction_glob, input_xlsx_factory
    ):
        mock_transaction_glob(
            input_xlsx_factory(breeds=[breed_row(stock_group="Sheep Merino")])
        )
        assert extract_lambing_calving_rate("Sheep Nonexistent") == {
            "ewesLambing": {"autumn": 0, "winter": 0, "spring": 0, "summer": 0}
        }


class TestExtractBreedRateSeasonalLambing:
    """The "Lambs/Calfs marking Rate {Season}" columns.

    Sheep-only in the payload: beef_annual_data has no seasonalLambing key, and
    extract_annual_data only requests it for sheep. This reads the same column
    template as cowsCalving -- see the AIA-shape note on
    TestExtractLambingCalvingRate for why ewesLambing reads a different one.
    """

    def test_exact_column_mapping(self, mock_transaction_glob, input_xlsx_factory):
        mock_transaction_glob(
            input_xlsx_factory(
                breeds=[breed_row(stock_group="Sheep Merino", marking=(11, 22, 33, 44))]
            )
        )
        assert extract_breed_rate("Sheep Merino", "seasonalLambing") == {
            "seasonalLambing": {
                "autumn": 11,
                "winter": 44,
                "spring": 22,
                "summer": 33,
            }
        }

    def test_stock_group_absent_from_the_sheet_yields_zeros(
        self, mock_transaction_glob, input_xlsx_factory
    ):
        mock_transaction_glob(
            input_xlsx_factory(breeds=[breed_row(stock_group="Sheep Merino")])
        )
        assert extract_breed_rate("Sheep Nonexistent", "seasonalLambing") == {
            "seasonalLambing": {"autumn": 0, "winter": 0, "spring": 0, "summer": 0}
        }
