from copy import deepcopy

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
    "purchases": [{"head": 0, "purchaseSource": "", "purchaseWeight": 0}],
}
