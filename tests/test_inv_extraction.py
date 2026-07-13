from internal.inv_extraction import (
    OTHER_N_FERTILISERS,
    build_purchase_entry,
    extract_chemical_data,
    extract_electricity_data,
    extract_feed_data,
    extract_fertiliser_data,
    extract_fuel_data,
    extract_lambing_calving_rate,
    extract_lime_data,
    extract_seasonal_row_data,
    extract_seasonalLambing_rate,
    extract_supplementation_data,
    extract_wool_row_data,
)

from tests.conftest import annual_row, seasonal_row

SEASONS = ["autumn", "winter", "spring", "summer"]

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
    assert OTHER_N_FERTILISERS == [
        "Monoammonium phosphate (MAP)",
        "Diammonium Phosphate (DAP)",
        "Urea-Ammonium Nitrate (UAN)",
        "Ammonium Nitrate (AN)",
        "Calcium Ammonium Nitrate (CAN)",
        "Triple Superphosphate (TSP)",
        "Super Potash 1:1",
        "Super Potash 2:1",
        "Super Potash 3:1",
        "Super Potash 4:1",
        "Super Potash 5:1",
        "Muriate of Potash",
        "Sulphate of Potash",
        "Sulphate of Ammonia",
    ]


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
                "head": 10, "liveweight": 1, "liveweightGain": 0.1,
                "crudeProtein": 11, "dryMatterDigestibility": 21, "feedAvailability": 31,
            },
            "winter": {
                "head": 20, "liveweight": 2, "liveweightGain": 0.2,
                "crudeProtein": 12, "dryMatterDigestibility": 22, "feedAvailability": 32,
            },
            "spring": {
                "head": 30, "liveweight": 3, "liveweightGain": 0.3,
                "crudeProtein": 13, "dryMatterDigestibility": 23, "feedAvailability": 33,
            },
            "summer": {
                "head": 40, "liveweight": 4, "liveweightGain": 0.4,
                "crudeProtein": 14, "dryMatterDigestibility": 24, "feedAvailability": 34,
            },
        }

    def test_optional_fields_omitted_entirely_when_none(self):
        row = seasonal_row(head=(10, 20, 30, 40))
        result = extract_seasonal_row_data(row)
        for season in SEASONS:
            assert set(result[season].keys()) == {"head", "liveweight", "liveweightGain"}

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

    def test_clean_wool_yield_none_defaults_to_zero(self):
        row = seasonal_row(clean_wool_yield=None)
        assert extract_wool_row_data(row)["cleanWoolYield"] == 0

    def test_head_shorn_and_wool_shorn_pass_raw_none_through_unguarded(self):
        row = seasonal_row(head_shorn=None, wool_shorn=None, clean_wool_yield=None)
        assert extract_wool_row_data(row) == {
            "headShorn": None,
            "woolShorn": None,
            "cleanWoolYield": 0,
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


class TestExtractLimeData:
    def test_maps_row_2_id_is_untouched_row_3_and_4_are_limestone(self):
        json_data = {"beef": [{}]}
        row = annual_row(id_value="GroupA", limestone=250, limestone_fraction=0.75)
        result = extract_lime_data(json_data, row, "beef", 0)
        assert result["beef"][0]["limestone"] == 250
        assert result["beef"][0]["limestoneFraction"] == 0.75


class TestExtractFertiliserData:
    def test_exact_column_mapping(self):
        json_data = {"beef": [{}]}
        row = annual_row(
            single_super=11,
            pasture_dryland=22,
            crops_dryland=33,
            other_ferts=tuple(range(100, 114)),
        )
        result = extract_fertiliser_data(json_data, row, "beef", 0)
        fert = result["beef"][0]["fertiliser"]
        assert fert["singleSuperphosphate"] == 11
        assert fert["pastureDryland"] == 22
        assert fert["pastureIrrigated"] == 0
        assert fert["cropsDryland"] == 33
        assert fert["cropsIrrigated"] == 0
        assert len(fert["otherFertilisers"]) == 14
        for idx, entry in enumerate(fert["otherFertilisers"]):
            assert entry["otherDryland"] == 100 + idx
            assert entry["otherIrrigated"] == 0
            assert entry["otherType"] == OTHER_N_FERTILISERS[idx]


class TestExtractFuelData:
    def test_exact_column_mapping(self):
        json_data = {"beef": [{}]}
        row = annual_row(diesel=111, petrol=222, lpg=333)
        result = extract_fuel_data(json_data, row, "beef", 0)
        assert result["beef"][0]["diesel"] == 111
        assert result["beef"][0]["petrol"] == 222
        assert result["beef"][0]["lpg"] == 333


class TestExtractSupplementationData:
    def test_exact_column_mapping(self):
        json_data = {"beef": [{}]}
        row = annual_row(mineral=(1, 2, 3, 4, 5, 6))
        result = extract_supplementation_data(json_data, row, "beef", 0)
        assert result["beef"][0]["mineralSupplementation"] == {
            "mineralBlock": 1,
            "mineralBlockUrea": 2,
            "weanerBlock": 3,
            "weanerBlockUrea": 4,
            "drySeasonMix": 5,
            "drySeasonMixUrea": 6,
        }


class TestExtractElectricityData:
    # "Electricity source" is a two-value Excel dropdown (State Grid / Renewable),
    # so only those two inputs are exercised here.
    def test_state_grid_includes_renewable_field(self):
        json_data = {"beef": [{}]}
        row = annual_row(electricity_source="State Grid", electricity_renewable=500, electricity_use=5000)
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


class TestExtractChemicalData:
    def test_exact_column_mapping(self):
        json_data = {"beef": [{}]}
        row = annual_row(herbicide=7, herbicide_other=8)
        result = extract_chemical_data(json_data, row, "beef", 0)
        assert result["beef"][0]["herbicide"] == 7
        assert result["beef"][0]["herbicideOther"] == 8


class TestExtractLambingCalvingRate:
    def test_sheep_uses_ewes_lambing_key(self):
        json_data = {"sheep": [{}]}
        row = annual_row(repro_rates=(11, 22, 33, 44))
        result = extract_lambing_calving_rate(json_data, row, "sheep", 0)
        assert result["sheep"][0]["ewesLambing"] == {
            "autumn": 11, "winter": 22, "spring": 33, "summer": 44,
        }
        assert "cowsCalving" not in result["sheep"][0]

    def test_beef_uses_cows_calving_key(self):
        json_data = {"beef": [{}]}
        row = annual_row(repro_rates=(11, 22, 33, 44))
        result = extract_lambing_calving_rate(json_data, row, "beef", 0)
        assert result["beef"][0]["cowsCalving"] == {
            "autumn": 11, "winter": 22, "spring": 33, "summer": 44,
        }
        assert "ewesLambing" not in result["beef"][0]


class TestExtractSeasonalLambingRate:
    def test_exact_column_mapping(self):
        json_data = {"sheep": [{}]}
        row = annual_row(seasonal_lambing=(11, 22, 33, 44))
        result = extract_seasonalLambing_rate(json_data, row, "sheep", 0)
        assert result["sheep"][0]["seasonalLambing"] == {
            "autumn": 11, "winter": 22, "spring": 33, "summer": 44,
        }

    def test_has_no_species_gating_of_its_own(self):
        # extract_seasonalLambing_rate is callable regardless of species -- the
        # sheep-only restriction lives in the caller (extract_annual_data), not here.
        json_data = {"beef": [{}]}
        row = annual_row(seasonal_lambing=(1, 2, 3, 4))
        result = extract_seasonalLambing_rate(json_data, row, "beef", 0)
        assert result["beef"][0]["seasonalLambing"] == {
            "autumn": 1, "winter": 2, "spring": 3, "summer": 4,
        }
