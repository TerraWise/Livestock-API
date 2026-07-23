from copy import deepcopy

OTHER_N_FERTILISERS = [
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

SEASONS = ["autumn", "winter", "spring", "summer"]

OPTIONAL_SEASON_FIELDS = (
    (12, "crudeProtein"),
    (16, "dryMatterDigestibility"),
    (20, "feedAvailability"),
)

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

# Stock class specific seasonal data
beef_seasonal_stock_class_data = {"head": 0, "liveweight": 0.0, "liveweightGain": 0.0}

# Stock class specific annual data
beef_annual_stock_class_data = {
    "autumn": deepcopy(beef_seasonal_stock_class_data),
    "winter": deepcopy(beef_seasonal_stock_class_data),
    "spring": deepcopy(beef_seasonal_stock_class_data),
    "summer": deepcopy(beef_seasonal_stock_class_data),
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
        "otherFertilisers": [
            {"otherDryland": 0, "otherIrrigated": 0, "otherType": name}
            for name in OTHER_N_FERTILISERS
        ],
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

# Stock class specific seasonal data
sheep_seasonal_stock_class_data = {"head": 0, "liveweight": 0.0, "liveweightGain": 0.0}

# Stock class specific annual data
sheep_annual_stock_class_data = {
    "autumn": deepcopy(sheep_seasonal_stock_class_data),
    "winter": deepcopy(sheep_seasonal_stock_class_data),
    "spring": deepcopy(sheep_seasonal_stock_class_data),
    "summer": deepcopy(sheep_seasonal_stock_class_data),
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
        "otherFertilisers": [
            {"otherDryland": 0, "otherIrrigated": 0, "otherType": name}
            for name in OTHER_N_FERTILISERS
        ],
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
