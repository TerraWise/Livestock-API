from copy import deepcopy
from typing import TYPE_CHECKING

from openpyxl import Workbook
import glob, os
import pandas as pd

from internal.constant import (
    OTHER_N_FERTILISERS,
    SEASONS,
    OPTIONAL_SEASON_FIELDS,
    ANNUAL_DATA_DEFAULTS,
)

if TYPE_CHECKING:
    from internal.stock_class import Livestock


def extract_seasonal_data(inventory_sheet: Workbook) -> dict:
    seasonal_data = {}
    seasonal_sheet = inventory_sheet["Seasonal Data"]

    row_num = 2
    for row in seasonal_sheet.iter_rows(
        min_row=2, min_col=1, max_row=34, values_only=True
    ):
        if row[0] is None:
            break
        stock, stock_id, stock_class = row[0], row[1], row[3]
        if stock_id is None:
            stock_id = ""
        stock = stock.lower()
        seasonal_data.setdefault(stock, {})
        seasonal_data[stock].setdefault(stock_id, {})[stock_class] = {}
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
        seasonal_data[stock][stock_id].update(
            extract_lambing_calving_rate(f"{stock.capitalize()} {stock_id}")
        )
        seasonal_data[stock][stock_id].update(
            extract_seasonalLambing_rate(f"{stock.capitalize()} {stock_id}")
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
        "cleanWoolYield": row[30] if row[30] is not None else 0,
    }


def extract_transaction_data(stock_cat: str, stock_id: str, stock_class: str) -> dict:
    path = glob.glob(os.path.join("input", "*.xlsm"))
    transaction_df = pd.read_excel(path[0], "Transaction")

    stock_group = f"{stock_cat} {stock_id}" if stock_id else stock_cat
    filtered_df = transaction_df.loc[
        transaction_df["Stock group"].str.lower().eq(stock_group)
        & transaction_df["Code name"].eq(stock_class)
    ]

    if filtered_df.empty:
        return {
            "headSold": 0,
            "saleWeight": 0,
            "purchases": [build_purchase_entry(stock_cat, 0, 0)],
        }

    head_sold = filtered_df["Quantity"].sum()
    sale_weight = (
        sum(filtered_df["Average liveweight (kg/hd)"] * filtered_df["Quantity"])
        / head_sold
        if head_sold
        else 0
    )
    transaction_data = {
        "headSold": head_sold,
        "saleWeight": sale_weight,
        "purchases": [],
    }

    purchases_df = filtered_df.loc[filtered_df["Transaction type"] == "Purchase"]
    if purchases_df.empty:
        transaction_data["purchases"].append(build_purchase_entry(stock_cat, 0, 0))
        return transaction_data

    for _, r in purchases_df.iterrows():
        source = r["Source"] if stock_cat == "beef" else ""
        transaction_data["purchases"].append(
            build_purchase_entry(
                stock_cat, r["Quantity"], r["Average liveweight (kg/hd)"], source
            )
        )

    return transaction_data


def extract_lambing_calving_rate(stock_group: str) -> dict:
    path = glob.glob(os.path.join("input", "*.xlsm"))
    reproduction_df = pd.read_excel(path[0], "Annual Data - Breed")
    reproduction_df.set_index(reproduction_df.columns[0], inplace=True)
    if "sheep" in stock_group.lower():
        repro = "ewesLambing"
    else:
        repro = "cowsCalving"

    reproduction_data = {repro: {}}
    for s in SEASONS:
        if stock_group in reproduction_df.index:
            reproduction_data[repro][s] = reproduction_df.loc[stock_group, f"Lambs/Calfs marking Rate {s.capitalize()}"]
        else:
            reproduction_data[repro][s] = 0

    return reproduction_data


def extract_seasonalLambing_rate(stock_group: str) -> dict:
    path = glob.glob(os.path.join("input", "*.xlsm"))
    reproduction_df = pd.read_excel(path[0], "Annual Data - Breed")
    reproduction_df.set_index(reproduction_df.columns[0], inplace=True)

    metric = "seasonalLambing"
    lambing_data = {metric: {}}
    for s in SEASONS:
        if stock_group in reproduction_df.index:
            lambing_data[metric][s] = reproduction_df.loc[stock_group, f"Proportion of ewes lambing/cows calving {s.capitalize()}"]
        else:
            lambing_data[metric][s] = 0

    return lambing_data


def build_purchase_entry(stock, head, weight, source="Dairy origin"):
    entry = {"head": head, "purchaseWeight": weight}
    if stock == "beef":
        entry["purchaseSource"] = source
    return entry


def extract_lime_data(
    json_data: dict,
    row: tuple,
    livestock: str,
    group: int = 0,
) -> dict:
    json_data[livestock][group]["limestone"] = row[1]
    json_data[livestock][group]["limestoneFraction"] = row[2]

    return json_data


def extract_fertiliser_data(
    json_data: dict,
    row: tuple,
    livestock: str,
    group: int = 0,
) -> dict:
    json_data[livestock][group]["fertiliser"] = {
        "singleSuperphosphate": row[3],
        "pastureDryland": row[4],  # Urea pasture
        "pastureIrrigated": 0,
        "cropsDryland": 0,  # Urea crop
        "cropsIrrigated": 0,
        "otherFertilisers": [],
    }

    for i in range(6, 20):
        json_data[livestock][group]["fertiliser"]["otherFertilisers"].append(
            {
                "otherDryland": row[i],
                "otherIrrigated": 0,  # Assuming no irrigated data for other fertilisers
                "otherType": OTHER_N_FERTILISERS[i - 6],
            }
        )

    return json_data


def extract_fuel_data(
    json_data: dict,
    row: tuple,
    livestock: str,
    group: int = 0,
) -> dict:
    json_data[livestock][group]["diesel"] = row[20]

    json_data[livestock][group]["petrol"] = row[21]

    json_data[livestock][group]["lpg"] = row[22]

    return json_data


def extract_supplementation_data(
    json_data: dict,
    row: tuple,
    livestock: str,
    group: int = 0,
) -> dict:
    json_data[livestock][group]["mineralSupplementation"] = {
        "mineralBlock": row[23],
        "mineralBlockUrea": row[24],
        "weanerBlock": row[25],
        "weanerBlockUrea": row[26],
        "drySeasonMix": row[27],
        "drySeasonMixUrea": row[28],
    }

    return json_data


def extract_electricity_data(
    json_data: dict,
    row: tuple,
    livestock: str,
    group: int = 0,
) -> dict:
    json_data[livestock][group]["electricitySource"] = (
        row[29] if row[29] else "State Grid"
    )
    if row[29] != "Renewable":
        json_data[livestock][group]["electricityRenewable"] = row[30]
    json_data[livestock][group]["electricityUse"] = row[31]

    return json_data


def extract_feed_data(
    json_data: dict,
    row: tuple,
    livestock: str,
    group: int = 0,
) -> dict:
    json_data[livestock][group]["grainFeed"] = row[32]
    json_data[livestock][group]["hayFeed"] = row[33]
    if livestock == "beef":
        json_data[livestock][group]["cottonseedFeed"] = row[34]

    return json_data


def extract_chemical_data(
    json_data: dict,
    row: tuple,
    livestock: str,
    group: int = 0,
) -> dict:
    json_data[livestock][group]["herbicide"] = row[35]
    json_data[livestock][group]["herbicideOther"] = row[36]

    return json_data


def extract_merino_pct(
    json_data: dict,
    livestock: str,
    group: int = 0,
) -> dict:
    path = glob.glob(os.path.join("input", "*.xlsm"))
    transaction_df = pd.read_excel(path[0], "Transaction")

    stock_group = livestock + (
        " " + json_data[livestock][group]["id"]
        if not pd.isna(json_data[livestock][group]["id"])
        else ""
    )
    filtered_df = transaction_df.loc[
        transaction_df["Stock group"].eq(stock_group)
        & transaction_df["Transaction type"].eq("Purchase")
    ]

    if filtered_df.empty:
        json_data[livestock][group]["merinoPercent"] = 0
        return json_data

    total_head = filtered_df["Quantity"].sum()
    merino_pct = (
        filtered_df["Merino sheep purchased (head)"].sum() / total_head
        if total_head
        else 0
    )
    json_data[livestock][group]["merinoPercent"] = merino_pct

    return json_data


ANNUAL_DATA_EXTRACTORS = (
    extract_lime_data,
    extract_fertiliser_data,
    extract_fuel_data,
    extract_supplementation_data,
    extract_electricity_data,
    extract_feed_data,
    extract_chemical_data,
)


def extract_annual_data(inventory_sheet: Workbook, livestock: "Livestock") -> dict:
    annual_sheet = inventory_sheet["Annual Data - Enterprise"]
    json_data = livestock.metadata

    for group in json_data[livestock.species]:
        group.update(deepcopy(ANNUAL_DATA_DEFAULTS[livestock.species]))

    for row in annual_sheet.iter_rows(
        min_row=2, min_col=1, max_col=48, values_only=True
    ):
        if row[0] is None or row[0] == 0:
            break

        stock_cat = row[0]
        if stock_cat not in livestock.ids:
            continue
        i = livestock.ids.index(stock_cat)
        for extractor in ANNUAL_DATA_EXTRACTORS:
            json_data = extractor(json_data, row, livestock.species, i)

    if livestock.species == "sheep":
        # merinoPercent depends only on the Transaction sheet, not on any
        # Annual Data row, so it's computed once per group here rather than
        # inside the row loop above -- otherwise a group with zero matching
        # Annual Data rows would never get merinoPercent set at all.
        for i in range(len(json_data[livestock.species])):
            json_data = extract_merino_pct(json_data, livestock.species, i)

    return json_data
