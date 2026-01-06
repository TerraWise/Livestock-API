from copy import deepcopy

# Stock class list
stock_classes = [
    "rams",
    "tradeRams",
    "wethers",
    "tradeWethers",
    "maidenBreedingEwes",
    "tradeBreedingEwes",
    "breedingEwes",
    "tradeBreedingEwes",
    "otherEwes",
    "tradeOtherEwes",
    "eweLambs",
    "tradeEweLambs",
    "wetherLambs",
    "tradeWetherLambs",
    "tradeEwes",
    "tradeLambsAndHoggets"
]

# Seasonal list
seasons = [
    "autumn",
    "winter",
    "spring",
    "summer"
]

# Stock class specific seasonal data
seasonal_stock_class_data = {
    "head": 0,
    "liveweight": 0.0,
    "liveweightGain": 0.0
}

# Stock class specific annual data
annual_stock_class_data = {
    "autumn": deepcopy(seasonal_stock_class_data),
    "winter": deepcopy(seasonal_stock_class_data),
    "spring": deepcopy(seasonal_stock_class_data),
    "summer": deepcopy(seasonal_stock_class_data),
    "headShorn": 0,
    "woolShorn": 0,
    "cleanWoolYield": 0,
    "headSold": 0,
    "saleWeight": 0,
    "purchases": [
        {
            "head": 0,
            "purchaseWeight": 0
        }
    ]
}        