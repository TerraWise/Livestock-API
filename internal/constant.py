OTHER_N_FERTILISERS = {
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


SEASONS = ["autumn", "winter", "spring", "summer"]

OPTIONAL_SEASON_FIELDS = {
    "crudeProtein": "Crude protein (%)",
    "dryMatterDigestibility": "Dry matter digestibility (%)",
    "feedAvailability": "Feed availability (t/ha)",
}

ANNUAL_SCALAR_COLUMNS = {
    "limestone": "Mass of Lime Applied (total tonnes)",
    "limestoneFraction": "Fraction of Lime/Dolomite",
    "diesel": "Annual Diesel Consumption (litres/year)",
    "petrol": "Annual Petrol Use (litres/year)",
    "lpg": "Annual LPG Use (litres/year)",
    "herbicide": "Herbicide (Paraquat, Diquat, Glyphosate) (kg a.i.)",
    "herbicideOther": "General Herbicide/Pesticide use (kg a.i.)",
}

ANNUAL_NESTED_COLUMNS = {
    "mineralSupplementation": {
        "mineralBlock": "Mineral Block (t)",
        "mineralBlockUrea": "Mineral Block Urea (% Urea)",
        "weanerBlock": "Weaner Block (t)",
        "weanerBlockUrea": "Weaner Block Urea (% Urea)",
        "drySeasonMix": "Dry Season Mix (t)",
        "drySeasonMixUrea": "Dry Season Mix Urea (% Urea)",
    },
}

# Per-stock-class seasonal defaults. liveweight/liveweightGain must stay FLOAT:
# 0 == 0.0 in Python so the tests cannot tell them apart, but json.dumps emits
# "0" vs "0.0", so tidying these to int would change the bytes on the wire.
SEASONAL_STOCK_CLASS_DATA = {"head": 0, "liveweight": 0.0, "liveweightGain": 0.0}


def _season_defaults() -> dict:
    """A fresh {season: defaults} block, one distinct dict per season.

    Separate objects matter: aliasing them would make a write to one season's
    head land on all four, and deepcopy faithfully reproduces the aliasing, so
    the deepcopy-independence tests would not catch it.
    """
    return {season: dict(SEASONAL_STOCK_CLASS_DATA) for season in SEASONS}


def _other_fertiliser_defaults() -> list:
    """Zeroed entry per OTHER_N_FERTILISERS name, in list order.

    That order is load-bearing: extract_fertiliser_data pairs it positionally
    with the 14 contiguous sheet columns starting at index 6.
    """
    return [
        {"otherDryland": 0, "otherIrrigated": 0, "otherType": name}
        for name in OTHER_N_FERTILISERS
    ]


# Beef Stock class list
beef_stock_classes = [
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

# Stock class specific annual data
beef_annual_stock_class_data = {
    **_season_defaults(),
    "headSold": 0,
    "saleWeight": 0,
    "purchases": [{"head": 0, "purchaseSource": "Dairy origin", "purchaseWeight": 0}],
}

# Other annual data
beef_annual_data = {
    "limestone": 0,
    "limestoneFraction": 0,
    "fertiliser": {
        "singleSuperphosphate": 0,
        "pastureDryland": 0,
        "pastureIrrigated": 0,
        "cropsDryland": 0,
        "cropsIrrigated": 0,
        "otherFertilisers": _other_fertiliser_defaults(),
    },
    "diesel": 0,
    "petrol": 0,
    "lpg": 0,
    "mineralSupplementation": {
        "mineralBlock": 0,
        "mineralBlockUrea": 0,
        "weanerBlock": 0,
        "weanerBlockUrea": 0,
        "drySeasonMix": 0,
        "drySeasonMixUrea": 0,
    },
    "electricitySource": "State Grid",
    "electricityRenewable": 0,
    "electricityUse": 0,
    "grainFeed": 0,
    "hayFeed": 0,
    "cottonseedFeed": 0,
    "herbicide": 0,
    "herbicideOther": 0,
    "cowsCalving": {"autumn": 0, "winter": 0, "spring": 0, "summer": 0},
}

# Sheep Stock class list
sheep_stock_classes = [
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

# Stock class specific annual data
sheep_annual_stock_class_data = {
    **_season_defaults(),
    "headShorn": 0,
    "woolShorn": 0,
    "cleanWoolYield": 0,
    "headSold": 0,
    "saleWeight": 0,
    "purchases": [{"head": 0, "purchaseWeight": 0}],
}

# Other annual data
sheep_annual_data = {
    "limestone": 0,
    "limestoneFraction": 0,
    "fertiliser": {
        "singleSuperphosphate": 0,
        "pastureDryland": 0,
        "pastureIrrigated": 0,
        "cropsDryland": 0,
        "cropsIrrigated": 0,
        "otherFertilisers": _other_fertiliser_defaults(),
    },
    "diesel": 0,
    "petrol": 0,
    "lpg": 0,
    "mineralSupplementation": {
        "mineralBlock": 0,
        "mineralBlockUrea": 0,
        "weanerBlock": 0,
        "weanerBlockUrea": 0,
        "drySeasonMix": 0,
        "drySeasonMixUrea": 0,
    },
    "electricitySource": "State Grid",
    "electricityRenewable": 0,
    "electricityUse": 0,
    "grainFeed": 0,
    "hayFeed": 0,
    "herbicide": 0,
    "herbicideOther": 0,
    "ewesLambing": {"autumn": 0, "winter": 0, "spring": 0, "summer": 0},
    "seasonalLambing": {"autumn": 0, "winter": 0, "spring": 0, "summer": 0},
}

# Annual stock class data template per species
annual_stock_class_data = {
    "sheep": sheep_annual_stock_class_data,
    "beef": beef_annual_stock_class_data,
}

ANNUAL_DATA_DEFAULTS = {"sheep": sheep_annual_data, "beef": beef_annual_data}
