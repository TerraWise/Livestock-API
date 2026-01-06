from functions.vars import stock_classes, seasons, annual_stock_class_data
from copy import deepcopy

def create_json_data(seasonal_sheep: list, group: int = 1, **kwargs) -> dict:
    json_data = agro_zone(kwargs["northOfTropicOfCapricorn"], kwargs["rainfallAbove600mm"])

    # Create stock class data structure
    json_data["sheep"] = [
        {
            "classes": {}
        }
    ] * group

    json_data = stock_class_data(json_data, group, seasonal_sheep)

    return json_data

def agro_zone(northOfTropicOfCapricorn=False, rainfallAbove600mm=False) -> dict:
    return {
        "state": "wa_sw",
        "northOfTropicOfCapricorn": northOfTropicOfCapricorn,
        "rainfallAbove600": rainfallAbove600mm
    }

def seasonal_data(
    json_data: dict,
    stock_class: str,
    season: str,
    head: int,
    liveweight: float,
    liveweightGain: float,
    crudeProtein: float = 0,
    dryMatterDigestibility: float = 0,
    feedAvailability: float = 0,
    index: int = 0
) -> dict:
    json_data["sheep"][index]["classes"][stock_class][season]["head"] = head
    json_data["sheep"][index]["classes"][stock_class][season]["liveweight"] = liveweight
    json_data["sheep"][index]["classes"][stock_class][season]["liveweightGain"] = liveweightGain

    if crudeProtein > 0:
        json_data["sheep"][index]["classes"][stock_class][season]["crudeProtein"] = crudeProtein
    if dryMatterDigestibility > 0:
        json_data["sheep"][index]["classes"][stock_class][season]["dryMatterDigestibility"] = dryMatterDigestibility
    if feedAvailability > 0:
        json_data["sheep"][index]["classes"][stock_class][season]["feedAvailability"] = feedAvailability

    return json_data

def stock_class_data(
        json_data: dict,
        group: int,
        seasonal_sheep: list
) -> dict:
    for i in range(group):
        for stock_class in stock_classes:
            json_data["sheep"][i]["classes"][stock_class] = deepcopy(annual_stock_class_data)
            json_data["sheep"][i]["classes"][stock_class]["purchases"] = seasonal_sheep[i][stock_class]["purchases"]
            for season in seasons:
                seasonal_sheep_data = seasonal_sheep[i][stock_class][season]

                json_data = seasonal_data(
                    json_data,
                    stock_class,
                    season,
                    **seasonal_sheep_data,
                    index=i
                )

    return json_data