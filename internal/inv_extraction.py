from copy import deepcopy
from functools import lru_cache
from typing import TYPE_CHECKING

from openpyxl import Workbook
import glob, os
import pandas as pd

from internal.constant import (
    OTHER_N_FERTILISERS,
    SEASONS,
    OPTIONAL_SEASON_FIELDS,
    ANNUAL_DATA_DEFAULTS,
    ANNUAL_SCALAR_COLUMNS,
    ANNUAL_NESTED_COLUMNS,
)

if TYPE_CHECKING:
    from internal.stock_class import Livestock


def workbook_path() -> str:
    """Resolve the single input workbook.

    glob.glob is looked up on the module at call time and never bound with
    `from glob import glob` -- the tests monkeypatch "glob.glob", and that only
    works through the module attribute. Rebinding it here, caching the result,
    or taking the path as an argument would make those mocks stop applying
    silently, and the suite would start reading the real input/ workbook.

    The bare [0] is deliberate: the four call sites this replaces all raised
    IndexError on an empty input/, and that stays unchanged.
    """
    return glob.glob(os.path.join("input", "*.xlsm"))[0]


@lru_cache(maxsize=32)
def _read_sheet(path: str, sheet: str, _fingerprint: tuple) -> pd.DataFrame:
    """Memoised read. _fingerprint only participates in the cache key."""
    return pd.read_excel(path, sheet)


def read_sheet(sheet: str) -> pd.DataFrame:
    """Parse one sheet of the input workbook, memoised.

    Keyed on (path, sheet, mtime, size): the path keeps one test's temp
    workbook from serving the next one's read, and the stat pair catches a
    workbook rewritten in place. Reads stay per-sheet and lazy -- callers may
    ask for a sheet the file does not have, so nothing here may parse the
    workbook eagerly or validate its sheet names up front.

    Returns the SHARED cached frame. Never mutate it; see breed_table.
    """
    path = workbook_path()
    try:
        stat = os.stat(path)
        fingerprint = (stat.st_mtime_ns, stat.st_size)
    except OSError:
        fingerprint = ()
    return _read_sheet(path, sheet, fingerprint)


def clear_sheet_cache() -> None:
    """Drop every memoised sheet. Public so tests can reset between cases."""
    _read_sheet.cache_clear()


def transaction_table() -> pd.DataFrame:
    """The "Transaction" sheet. Read-only."""
    return read_sheet("Transaction")


def breed_table() -> pd.DataFrame:
    """ "Annual Data - Breed", indexed by its first (stock-group) column.

    set_index is deliberately not inplace. read_sheet hands back the shared
    cached frame, so re-indexing in place would leave the next caller with a
    frame whose first column is a rate, silently turning every subsequent
    lookup into a miss and every rate into 0.
    """
    frame = read_sheet("Annual Data - Breed")
    return frame.set_index(frame.columns[0])


def extract_seasonal_data(species: str) -> dict:
    seasonal_data = {}
    seasonal_sheet = read_sheet("Seasonal Data")

    for i, row in seasonal_sheet.iterrows():
        if pd.isna(row.loc["Stock category"]):
            raise ValueError(f"Missing value in seasonal data row: {i+2}")
        if row.loc["Stock category"].lower() != species:
            continue

        stock, stock_class = (
            row.loc["Stock category"].lower(),
            row.loc["Code name"],
        )
        stock_id = row.loc["ID"] if not pd.isna(row.loc["ID"]) else ""

        class_data = extract_seasonal_row_data(row)
        if stock == "sheep":
            class_data.update(extract_wool_row_data(row))
        class_data.update(extract_transaction_data(stock, stock_id, stock_class))

        groups = seasonal_data.setdefault(stock, {})
        groups.setdefault(stock_id, {})[stock_class] = class_data

    return seasonal_data


def extract_seasonal_row_data(r: pd.Series) -> dict:
    stock_data = {}

    for s in SEASONS:
        stock_data[s] = {
            "head": r.loc[f"Stock number (head) - {s.capitalize()}"],
            "liveweight": r.loc[f"Live weight (kg/head) - {s.capitalize()}"],
            "liveweightGain": r.loc[f"Live weight gain (kg/day) - {s.capitalize()}"],
        }
        for key, val in OPTIONAL_SEASON_FIELDS.items():
            if pd.notna(r.loc[f"{val} - {s.capitalize()}"]):
                stock_data[s][key] = r.loc[f"{val} - {s.capitalize()}"]

    return stock_data


def extract_wool_row_data(r: pd.Series) -> dict:
    return {
        "headShorn": r.loc["Head shorn (hd)"],
        "woolShorn": r.loc["Wool shorn (kg/hd)"],
        "cleanWoolYield": r.loc["Clean wool yield (%)"],
    }


def safe_ratio(numerator, denominator):
    """Divide, treating a zero denominator as 0 rather than NaN.

    Both Transaction aggregations can match rows whose quantities sum to zero.
    Pandas would give NaN there, which serialises to a JSON null the API
    rejects, so every such division goes through here.
    """
    return numerator / denominator if denominator else 0


def extract_transaction_data(stock_cat: str, stock_id: str, stock_class: str) -> dict:
    transaction_df = transaction_table()

    # NOTE: only the Stock group column is case-folded, not the key built here,
    # so this never matches an id containing an uppercase letter.
    # extract_merino_pct builds the same key a third way. Left as-is
    # deliberately: reconciling them changes behaviour, which is not this
    # change's job.
    stock_group = f"{stock_cat} {stock_id}" if stock_id else stock_cat
    filtered_df = transaction_df.loc[
        transaction_df["Stock group"].str.lower().eq(stock_group.lower())
        & transaction_df["Code name"].eq(stock_class)
    ]

    if filtered_df.empty:
        return {
            "headSold": 0,
            "saleWeight": 0,
            "purchases": [build_purchase_entry(stock_cat, 0, 0)],
        }

    sales_df = filtered_df.loc[filtered_df["Transaction type"] == "Sale"]
    transaction_data = {
        "headSold": sales_df["Quantity"].sum(),
        "saleWeight": safe_ratio(
            sum(sales_df["Average liveweight (kg/hd)"] * sales_df["Quantity"]),
            sales_df["Quantity"].sum(),
        ),
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


# Payload key -> the "Annual Data - Breed" column header it reads.
#
# The marking rate is published under a different name per species, from the
# same sheet column -- that is the fact being recorded here, not duplication.
# SEASONAL_LAMBING_KEY is sheep-only: cattle have no counterpart, and
# beef_annual_data carries no such key, so it must never be written to a beef
# group. extract_annual_data is what enforces that.
MARKING_RATE_KEY = {"sheep": "ewesLambing", "beef": "cowsCalving"}
SEASONAL_LAMBING_KEY = "seasonalLambing"

BREED_RATE_COLUMNS = {
    "ewesLambing": "Proportion of ewes lambing/cows calving {season}",
    "cowsCalving": "Lambs/Calfs marking Rate {season}",
    SEASONAL_LAMBING_KEY: "Lambs/Calfs marking Rate {season}",
}


def extract_breed_rate(stock_group: str, key: str) -> dict:
    """One four-season rate block from "Annual Data - Breed".

    Columns are matched by name, so the sheet's physical Autumn/Spring/Summer/
    Winter order maps correctly onto SEASONS whatever order SEASONS is in. A
    stock group with no row on the sheet reads as zeros.
    """
    template = BREED_RATE_COLUMNS[key]
    breeds = breed_table()
    present = stock_group in breeds.index
    return {
        key: {
            season: (
                breeds.loc[stock_group, template.format(season=season.capitalize())]
                if present
                else 0
            )
            for season in SEASONS
        }
    }


def extract_lambing_calving_rate(stock_group: str) -> dict:
    """The marking-rate block, under the key matching the group's species.

    NOTE: the species is recovered by looking for "sheep" in the group label,
    even though every caller already knows it -- so a beef breed whose name
    contained "sheep" would be published as ewesLambing.
    """
    key = "ewesLambing" if "sheep" in stock_group.lower() else "cowsCalving"
    return extract_breed_rate(stock_group, key)


def build_purchase_entry(stock, head, weight, source="Dairy origin"):
    entry = {"head": head, "purchaseWeight": weight}
    if stock == "beef":
        entry["purchaseSource"] = source
    return entry


def extract_column_data(
    json_data: dict,
    row: pd.Series,
    livestock: str,
    group: int = 0,
) -> dict:
    """Apply the straight column->field tables to one group.
    For lime, fuel, supplementation and chemical extractors,
    """
    entry = json_data[livestock][group]

    for key, column in ANNUAL_SCALAR_COLUMNS.items():
        entry[key] = row.loc[column]
    for key, columns in ANNUAL_NESTED_COLUMNS.items():
        entry[key] = {sub: row.loc[column] for sub, column in columns.items()}

    return json_data


def extract_fertiliser_data(
    json_data: dict,
    row: pd.Series,
    livestock: str,
    group: int = 0,
) -> dict:
    json_data[livestock][group]["fertiliser"] = {
        "singleSuperphosphate": row.loc["SSP"],
        "pastureDryland": row.loc["Urea Pasture"],
        "pastureIrrigated": 0,
        "cropsDryland": 0,  # Urea crop
        "cropsIrrigated": 0,
        "otherFertilisers": [],
    }

    for key, col in OTHER_N_FERTILISERS.items():
        json_data[livestock][group]["fertiliser"]["otherFertilisers"].append(
            {
                "otherDryland": row.loc[col],
                "otherIrrigated": 0,  # Assuming no irrigated data for other fertilisers
                "otherType": key,
            }
        )

    return json_data


def extract_electricity_data(
    json_data: dict,
    row: pd.Series,
    livestock: str,
    group: int = 0,
) -> dict:
    json_data[livestock][group]["electricitySource"] = row.loc["Electricity source"]
    if row.loc["Electricity source"] != "Renewable":
        json_data[livestock][group]["electricityRenewable"] = (
            row.loc["% of electricity from renewable source"]
            if pd.notna(row.loc["% of electricity from renewable source"])
            else 0
        )
    json_data[livestock][group]["electricityUse"] = (
        row.loc["Annual Electricity Use (total) (KWh)"]
        if pd.notna(row.loc["Annual Electricity Use (total) (KWh)"])
        else 0
    )

    return json_data


def extract_feed_data(
    json_data: dict,
    row: pd.Series,
    livestock: str,
    group: int = 0,
) -> dict:
    json_data[livestock][group]["grainFeed"] = row.loc["Grain purchased for feed (t)"]
    json_data[livestock][group]["hayFeed"] = row.loc["Hay purchased for feed (t)"]
    if livestock == "beef":
        json_data[livestock][group]["cottonseedFeed"] = row.loc[
            "Cotton seed for cattle (t)"
        ]

    return json_data


def extract_merino_pct(
    json_data: dict,
    livestock: str,
    group: int = 0,
) -> dict:
    transaction_df = transaction_table()

    # NOTE: a third way of building the group key, and the only one that folds
    # neither side's case. The pd.isna guard also never fires -- "id" is always
    # a str -- so a blank id yields a trailing space. Left as-is deliberately:
    # see the note in extract_transaction_data.
    stock_group = livestock + (
        (" " + json_data[livestock][group]["id"].lower())
        if json_data[livestock][group]["id"] != ""
        else ""
    )
    filtered_df = transaction_df.loc[
        transaction_df["Stock group"].str.lower().eq(stock_group)
        & transaction_df["Transaction type"].eq("Purchase")
    ]

    if filtered_df.empty:
        json_data[livestock][group]["merinoPercent"] = 0
        return json_data

    json_data[livestock][group]["merinoPercent"] = safe_ratio(
        filtered_df["Merino sheep purchased (head)"].sum(),
        filtered_df["Quantity"].sum(),
    )

    return json_data


# Applied in order to every matching "Annual Data - Enterprise" row. Each
# mutates json_data[species][group] in place.
ANNUAL_DATA_EXTRACTORS = (
    extract_column_data,
    extract_fertiliser_data,
    extract_electricity_data,
    extract_feed_data,
)


def extract_annual_data(livestock: "Livestock") -> dict:
    annual_sheet = read_sheet("Annual Data - Enterprise")
    json_data = livestock.metadata

    for group in json_data[livestock.species]:
        group.update(deepcopy(ANNUAL_DATA_DEFAULTS[livestock.species]))

    for i, row in annual_sheet.iterrows():
        if pd.isna(row.loc["Stock category"]):
            break

        stock_cat = row.loc["Stock category"]
        if stock_cat not in livestock.ids:
            continue
        i = livestock.ids.index(stock_cat)
        for extractor in ANNUAL_DATA_EXTRACTORS:
            extractor(json_data, row, livestock.species, i)

    # Per-group fields, computed after the row loop because they come from
    # other sheets and so must land on every group, including ones with no
    # Annual Data row of their own.
    species = livestock.species
    for i, group in enumerate(json_data[species]):
        # Matches "Annual Data - Breed" column A, which is "<Category> <Breed>".
        label = f"{species.capitalize()} {group['id']}"
        group.update(extract_breed_rate(label, MARKING_RATE_KEY[species]))
        if species == "sheep":
            # seasonalLambing and merinoPercent are sheep-only -- beef has no
            # such keys in its payload template.
            group.update(extract_breed_rate(label, SEASONAL_LAMBING_KEY))
            extract_merino_pct(json_data, species, i)

    return json_data
