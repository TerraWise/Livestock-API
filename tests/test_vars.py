from copy import deepcopy

from internal.beef_vars import beef_annual_stock_class_data, beef_stock_classes
from internal.sheep_vars import sheep_annual_stock_class_data, sheep_stock_classes

SEASONS = ["autumn", "winter", "spring", "summer"]


def test_beef_stock_classes_exact_list_and_order():
    assert beef_stock_classes == [
        "bullsGt1",
        "bullsGt1Traded",
        "cowsGt2",
        "cowsGt2Traded",
        "heifers1To2",
        "heifers1To2Traded",
        "heifersGt2",
        "heifersGt2Traded",
        "heifersLt1",
        "heifersLt1Traded",
        "steers1To2",
        "steers1To2Traded",
        "steersGt2",
        "steersGt2Traded",
        "steersLt1",
        "steersLt1Traded",
    ]


def test_sheep_stock_classes_exact_list_and_order():
    assert sheep_stock_classes == [
        "breedingEwes",
        "eweLambs",
        "wetherLambs",
        "maidenBreedingEwes",
        "otherEwes",
        "rams",
        "tradeBreedingEwes",
        "tradeEweLambs",
        "tradeMaidenBreedingEwes",
        "tradeOtherEwes",
        "tradeRams",
        "tradeWetherLambs",
        "tradeWethers",
        "wethers",
    ]


def test_beef_purchase_template_defaults_to_dairy_origin():
    assert beef_annual_stock_class_data["purchases"][0]["purchaseSource"] == "Dairy origin"


def test_sheep_purchase_template_has_no_purchase_source_key():
    assert "purchaseSource" not in sheep_annual_stock_class_data["purchases"][0]


def test_beef_season_defaults():
    for season in SEASONS:
        assert beef_annual_stock_class_data[season] == {
            "head": 0,
            "liveweight": 0.0,
            "liveweightGain": 0.0,
        }


def test_sheep_season_defaults():
    for season in SEASONS:
        assert sheep_annual_stock_class_data[season] == {
            "head": 0,
            "liveweight": 0.0,
            "liveweightGain": 0.0,
        }


def test_sheep_template_has_wool_fields_beef_does_not():
    for key in ("headShorn", "woolShorn", "cleanWoolYield"):
        assert key in sheep_annual_stock_class_data
        assert key not in beef_annual_stock_class_data


def test_deepcopy_independence_beef():
    a = deepcopy(beef_annual_stock_class_data)
    b = deepcopy(beef_annual_stock_class_data)
    a["purchases"][0]["purchaseSource"] = "mutated"
    a["autumn"]["head"] = 999
    assert b["purchases"][0]["purchaseSource"] == "Dairy origin"
    assert b["autumn"]["head"] == 0
    assert beef_annual_stock_class_data["purchases"][0]["purchaseSource"] == "Dairy origin"
    assert beef_annual_stock_class_data["autumn"]["head"] == 0


def test_deepcopy_independence_sheep():
    a = deepcopy(sheep_annual_stock_class_data)
    b = deepcopy(sheep_annual_stock_class_data)
    a["purchases"][0]["head"] = 999
    a["autumn"]["head"] = 999
    assert b["purchases"][0]["head"] == 0
    assert b["autumn"]["head"] == 0
    assert sheep_annual_stock_class_data["purchases"][0]["head"] == 0
    assert sheep_annual_stock_class_data["autumn"]["head"] == 0
