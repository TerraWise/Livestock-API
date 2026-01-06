from copy import deepcopy

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
