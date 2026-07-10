from openpyxl.worksheet.worksheet import Worksheet
from openpyxl import Workbook
import glob, os
import pandas as pd

from internal.sheep_vars import sheep_annual_stock_class_data
from internal.beef_vars import beef_annual_stock_class_data
from internal.stock_class import Livestock

SEASONS = ["autumn", "winter", "spring", "summer"]

OPTIONAL_SEASON_FIELDS = (
    (12, "crudeProtein"),
    (16, "dryMatterDigestibility"),
    (20, "feedAvailability"),
)

STOCK_CLASS_ANNUAL_DATA = [
    "headShorn",
    "woolShorn",
    "cleanWoolYield",
    "headSold",
    "saleWeight",
    "head",
    "purchaseWeight",
]

OTHER_N_FERTILISERS = [
    "Monoammonium phosphate (MAP)",
    "Diammonium phosphate (DAP)",
    "Urea-Ammonium Nitrate (UAN)",
    "Ammonium Nitrate (AN)",
    "Calcium Ammonium Nitrate (CAN)",
    "Tripple Superphosphate (TSP)",
    "Super Potash 1:1",
    "Super Potash 2:1",
    "Super Potash 3:1",
    "Super Potash 4:1",
    "Super Potash 5:1",
    "Muriate of Potash",
    "Sulphate of Potash",
    "Sulphate of Ammonia",
]


def extract_seasonal_data(inventory_sheet: Workbook) -> dict:
    seasonal_data = {}
    seasonal_sheet = inventory_sheet["Seasonal Data"]

    row_num = 2
    for row in seasonal_sheet.iter_rows(
        min_row=2, min_col=1, max_row=34, values_only=True
    ):
        stock, stock_id, stock_class = row[0], row[1], row[2]
        seasonal_data.setdefault(stock, {})
        seasonal_data[stock].setdefault(stock_id, {})[stock_class] = {}
        if row[0] is None:
            break
        if isinstance(row[0], str):
            if row[0].startswith("#"):
                raise ValueError(
                    f"Invalid data in Seasonal Data sheet at row {row_num}"
                )

        seasonal_data[stock][stock_id][stock_class] = extract_seasonal_row_data(row)
        if stock == "sheep":
            seasonal_data[stock][stock_id][stock_class].update(
                extract_wool_row_data(row)
            )

        seasonal_data[stock][stock_id][stock_class].update(
            extract_transaction_data(stock, stock_id, stock_class)
        )
        row_num += 1

    return seasonal_data


def extract_seasonal_row_data(row: tuple) -> dict:
    stock_data = {}

    for i in range(4, 8):
        season = SEASONS[i % 4]
        stock_data[season] = {
            "head": row[i],
            "liveweight": row[i + 4],
            "liveweightGain": row[i + 8],
        }
        for offset, key in OPTIONAL_SEASON_FIELDS:
            if row[i + offset] is not None:
                stock_data[season][key] = row[i + offset]

    return stock_data


def extract_wool_row_data(row: tuple) -> dict:
    return {
        "headShorn": row[28],
        "woolShorn": row[29],
        "cleanWoolYield": row[30],
    }


def extract_transaction_data(stock, stock_id, stock_class: str) -> dict:
    path = glob.glob(os.path.join("input", "*.xlsx"))
    transaction_df = pd.read_excel(path[0], "Transaction")

    stock_group = stock + " " + stock_id
    filtered_df = transaction_df.loc[
        (transaction_df["Stock group"] == stock_group)
        & (transaction_df["Stock class"] == stock_class)
    ]
    if filtered_df.empty:
        raise ValueError(
            f"No transaction data found for stock group '{stock_group}' and stock class '{stock_class}'"
        )

    head_sold = filtered_df["Head"].sum()
    sale_weight = (
        sum(filtered_df["Average liveweight (kg)"] * filtered_df["Head"]) / head_sold
    )
    transaction_data = {
        "headSold": head_sold,
        "saleWeight": sale_weight,
        "purchases": [],
    }

    purchases_df = filtered_df.loc[filtered_df["Transaction type"] == "Purchase"]
    if purchases_df.empty:
        transaction_data["purchases"].append(build_purchase_entry(stock, 0, 0))
        return transaction_data

    for _, r in purchases_df.iterrows():
        source = r["Source"] if stock == "beef" else ""
        transaction_data["purchases"].append(
            build_purchase_entry(stock, r["Head"], r["Average liveweight (kg)"], source)
        )

    return transaction_data


def build_purchase_entry(stock, head, weight, source=""):
    entry = {"head": head, "purchaseWeight": weight}
    if stock == "beef":
        entry["purchaseSource"] = source
    return entry


def extract_annual_data(inventory_sheet: Workbook, livestock: Livestock) -> dict:
    annual_sheet = inventory_sheet["Annual Data"]
    json_data = livestock.metadata

    for row in annual_sheet.iter_rows(
        min_row=2, min_col=1, max_col=45, values_only=True
    ):
        if row[0] is None:
            break

        i = livestock.ids.index(row[3]) if row[3] in livestock.ids else 0
        json_data = extract_lime_data(json_data, row, livestock.species, i)
        json_data = extract_fertiliser_data(json_data, row, livestock.species, i)
        json_data = extract_fuel_data(json_data, row, livestock.species, i)
        json_data = extract_supplementation_data(json_data, row, livestock.species, i)
        json_data = extract_electricity_data(json_data, row, livestock.species, i)
        json_data = extract_feed_data(json_data, row, livestock.species, i)
        json_data = extract_chemical_data(json_data, row, livestock.species, i)
        json_data = extract_lambing_calving_rate(
            json_data, annual_sheet, row, livestock
        )
        if livestock == "sheep":
            json_data = extract_merino_pct(json_data, annual_sheet, row, livestock)
            json_data = extract_seasonalLambing_rate(
                json_data, annual_sheet, row, livestock
            )

    return json_data


def extract_lime_data(
    json_data: dict,
    row: tuple,
    livestock: str,
    group: int = 0,
) -> dict:
    json_data[livestock][group]["limestone"] = row[4]
    json_data[livestock][group]["limestoneFraction"] = row[5]

    return json_data


def extract_fertiliser_data(
    json_data: dict,
    row: tuple,
    livestock: str,
    group: int = 0,
) -> dict:
    json_data[livestock][group]["fertiliser"] = {
        "singleSuperphosphate": row[6],
        "pastureDryland": row[7],  # Urea pasture
        "pastureIrrigated": 0,
        "cropsDryland": row[8],  # Urea crop
        "cropsIrrigated": 0,
        "otherFertilisers": [],
    }

    for i in range(9, 23):
        json_data[livestock][group]["fertiliser"]["otherFertilisers"].append(
            {
                "otherDryland": row[i],
                "otherIrrigated": 0,  # Assuming no irrigated data for other fertilisers
                "otherType": OTHER_N_FERTILISERS[i - 9],
            }
        )

    return json_data


def extract_fuel_data(
    json_data: dict,
    row: tuple,
    livestock: str,
    group: int = 0,
) -> dict:
    json_data[livestock][group]["diesel"] = row[23]

    json_data[livestock][group]["petrol"] = row[24]

    json_data[livestock][group]["lpg"] = row[25]

    return json_data


def extract_supplementation_data(
    json_data: dict,
    row: tuple,
    livestock: str,
    group: int = 0,
) -> dict:
    json_data[livestock][group]["mineralSupplementation"] = {
        "mineralBlock": row[26],
        "mineralBlockUrea": row[27],
        "weanerBlock": row[28],
        "weanerBlockUrea": row[29],
        "drySeasonMix": row[30],
        "drySeasonMixUrea": row[31],
    }

    return json_data


def extract_electricity_data(
    json_data: dict,
    row: tuple,
    livestock: str,
    group: int = 0,
) -> dict:
    json_data[livestock][group]["electricitySource"] = row[32]
    if row[32] != "Renewable":
        json_data[livestock][group]["electricityRenewable"] = row[33]
    json_data[livestock][group]["electricityUse"] = row[34]

    return json_data


def extract_feed_data(
    json_data: dict,
    row: tuple,
    livestock: str,
    group: int = 0,
) -> dict:
    json_data[livestock][group]["grainFeed"] = row[35]
    json_data[livestock][group]["hayFeed"] = row[36]
    if livestock == "beef":
        json_data[livestock][group]["cottonseedFeed"] = row[37]

    return json_data


def extract_chemical_data(
    json_data: dict,
    row: tuple,
    livestock: str,
    group: int = 0,
) -> dict:
    json_data[livestock][group]["herbicide"] = row[38]
    json_data[livestock][group]["herbicideOther"] = row[39]

    return json_data


def extract_merino_pct(
    json_data: dict,
    annual_sheet: Worksheet,
    row: int,
    livestock: str,
    group: int = 0,
) -> dict:
    json_data[livestock][group]["merinoPercent"] = annual_sheet.cell(row, 37).value

    return json_data


def extract_lambing_calving_rate(
    json_data: dict,
    row: tuple,
    livestock: str,
    group: int = 0,
) -> dict:
    season = annual_sheet.cell(row, 38).value
    rate = annual_sheet.cell(row, 39).value

    if livestock == "sheep":
        repro = "ewesLambing"
    else:
        repro = "cowsCalving"

    json_data[livestock][group][repro] = {
        "autumn": 0,
        "winter": 0,
        "spring": 0,
        "summer": 0,
    }
    json_data[livestock][group][repro][season.lower()] = rate  # type: ignore

    return json_data


def extract_seasonalLambing_rate(
    json_data: dict,
    annual_sheet: Worksheet,
    row: int,
    livestock: str,
    group: int = 0,
) -> dict:
    json_data[livestock][group]["seasonalLambing"] = {
        "autumn": 0,
        "winter": 0,
        "spring": 0,
        "summer": 0,
    }

    season = annual_sheet.cell(row, 40).value
    rate = annual_sheet.cell(row, 41).value

    json_data[livestock][group]["seasonalLambing"][season.lower()] = rate  # type: ignore

    return json_data
