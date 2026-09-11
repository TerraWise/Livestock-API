import itertools

import pandas as pd
import pytest
from openpyxl import Workbook

from internal import inv_extraction
from internal.constant import OTHER_N_FERTILISERS
from internal.stock_class import Beef, Sheep


@pytest.fixture(autouse=True)
def _isolate_sheet_cache():
    """Stop a memoised sheet from crossing a test boundary.

    Every factory call writes a new temp workbook, so a surviving cache entry
    would hand the next test the previous test's DataFrame -- silently, and
    with an outcome that depends on collection order. Cleared on both sides:
    before, so no test inherits a predecessor's frame; after, so nothing is
    left keyed on a tmp_path that is about to be deleted.
    """
    inv_extraction.clear_sheet_cache()
    yield
    inv_extraction.clear_sheet_cache()


def make_workbook(sheet_specs: dict) -> Workbook:
    """Build an in-memory Workbook from {sheet_name: [row_tuple, ...]}.

    Writes a blank row 1 first so data rows land on row 2, matching every
    extractor's min_row=2.
    """
    wb = Workbook()
    sheet_names = list(sheet_specs.keys())

    default_sheet = wb.active
    default_sheet.title = sheet_names[0]
    sheets = {sheet_names[0]: default_sheet}
    for name in sheet_names[1:]:
        sheets[name] = wb.create_sheet(name)

    for name, rows in sheet_specs.items():
        ws = sheets[name]
        width = len(rows[0]) if rows else 1
        ws.append([None] * width)
        for row in rows:
            ws.append(list(row))

    return wb


SEASONS = ("autumn", "winter", "spring", "summer")


def seasonal_row(
    stock="sheep",
    stock_id="GroupA",
    stock_class="breedingEwes",
    head=(100, 100, 100, 100),
    liveweight=(50, 50, 50, 50),
    liveweight_gain=(2, 2, 2, 2),
    crude_protein=(None, None, None, None),
    dry_matter_digestibility=(None, None, None, None),
    feed_availability=(None, None, None, None),
    head_shorn=100,
    wool_shorn=400,
    clean_wool_yield=0.9,
):
    """Build a "Seasonal Data" sheet row, indexed by real column name.

    The 4-tuples are ordered by constant.SEASONS (autumn, winter, spring,
    summer). Both this builder and extract_seasonal_row_data look columns up
    by name now, so the sheet's physical Autumn/Spring/Summer/Winter layout no
    longer has to match this order for a row to be read correctly.
    """
    row = {
        "Stock category": stock,
        "Code name": stock_class,
        "ID": stock_id,
        "Head shorn (hd)": head_shorn,
        "Wool shorn (kg/hd)": wool_shorn,
        "Clean wool yield (%)": clean_wool_yield,
    }
    for i, season in enumerate(SEASONS):
        cap = season.capitalize()
        row[f"Stock number (head) - {cap}"] = head[i]
        row[f"Live weight (kg/head) - {cap}"] = liveweight[i]
        row[f"Live weight gain (kg/day) - {cap}"] = liveweight_gain[i]
        row[f"Crude protein (%) - {cap}"] = crude_protein[i]
        row[f"Dry matter digestibility (%) - {cap}"] = dry_matter_digestibility[i]
        row[f"Feed availability (t/ha) - {cap}"] = feed_availability[i]
    return pd.Series(row)


# The only two values that ever appear in "Annual Data - Enterprise" column A.
# Annual data is collected per enterprise, not per breed, so the sheet carries
# exactly one row for each -- and main.py seeds every id list with the matching
# literal as group 0. Breed groups never have an Annual Data row of their own.
SHEEP_ENTERPRISE = "Sheep for allocation"
CATTLE_ENTERPRISE = "Cattle for allocation"


def annual_row(
    stock_cat=SHEEP_ENTERPRISE,
    limestone=200,
    limestone_fraction=0.5,
    single_super=10,
    pasture_dryland=20,
    other_ferts=tuple(range(1, 15)),
    diesel=1000,
    petrol=200,
    lpg=0,
    mineral=(0, 0, 0, 0, 0, 0),
    electricity_source="State Grid",
    electricity_renewable=500,
    electricity_use=5000,
    grain_feed=0,
    hay_feed=0,
    cottonseed_feed=0,
    herbicide=0,
    herbicide_other=0,
):
    """Build an "Annual Data - Enterprise" sheet row, indexed by real column name.

    "Stock category" is the sheet's single identity column, which
    extract_annual_data matches against livestock.ids. It is always
    SHEEP_ENTERPRISE or CATTLE_ENTERPRISE.

    "Urea Crop" is left unset because nothing reads it: extract_fertiliser_data
    hardcodes cropsDryland to 0.

    other_ferts is assigned to the sheet columns in OTHER_N_FERTILISERS' value
    order (the 14 short codes: MAP, DAP, ... SOA) -- the same order
    extract_fertiliser_data iterates.

    Reproduction rates are deliberately absent -- they live on the separate
    "Annual Data - Breed" sheet, keyed per breed. See breed_row.
    """
    row = {
        "Stock category": stock_cat,
        "Mass of Lime Applied (total tonnes)": limestone,
        "Fraction of Lime/Dolomite": limestone_fraction,
        "SSP": single_super,
        "Urea Pasture": pasture_dryland,
        "Annual Diesel Consumption (litres/year)": diesel,
        "Annual Petrol Use (litres/year)": petrol,
        "Annual LPG Use (litres/year)": lpg,
        "Mineral Block (t)": mineral[0],
        "Mineral Block Urea (% Urea)": mineral[1],
        "Weaner Block (t)": mineral[2],
        "Weaner Block Urea (% Urea)": mineral[3],
        "Dry Season Mix (t)": mineral[4],
        "Dry Season Mix Urea (% Urea)": mineral[5],
        "Electricity source": electricity_source,
        "% of electricity from renewable source": electricity_renewable,
        "Annual Electricity Use (total) (KWh)": electricity_use,
        "Grain purchased for feed (t)": grain_feed,
        "Hay purchased for feed (t)": hay_feed,
        "Cotton seed for cattle (t)": cottonseed_feed,
        "Herbicide (Paraquat, Diquat, Glyphosate) (kg a.i.)": herbicide,
        "General Herbicide/Pesticide use (kg a.i.)": herbicide_other,
    }
    for col, val in zip(OTHER_N_FERTILISERS.values(), other_ferts):
        row[col] = val
    return pd.Series(row)


def burning_row(
    fuel="coarse",
    season="early dry season",
    patchiness="high",
    rainfall_zone="low",
    years_since_last_fire=0,
    fire_scar_area=10,
    vegetation="Melaleuca woodland",
):
    """Build a 7-element "🔥Savannah burning" row tuple (columns A-G)."""
    return (
        fuel,
        season,
        patchiness,
        rainfall_zone,
        years_since_last_fire,
        fire_scar_area,
        vegetation,
    )


def veg_row(
    region="South West",
    tree_species="Mixed species (Environmental Plantings)",
    soil="Loams & Clays",
    area=50,
    age=5,
    beef_proportion=None,
    sheep_proportion=None,
):
    """Build a 10-element "🌿 Vegetation" row tuple (columns A-J).

    extract_veg_data reads min_col=2, so column A (index 0 here) is a
    required-but-unused placeholder. beef_proportion/sheep_proportion are
    always optional -- vegetation_planting itself defaults a None to [0].
    """
    return (
        None,
        region,
        tree_species,
        None,
        soil,
        area,
        None,
        age,
        beef_proportion,
        sheep_proportion,
    )


# "Transaction" sheet columns, as the source reads them. "Stock class" holds the
# human-readable label and "Code name" the camelCase key the extractors filter
# on -- the real sheet carries both.
TRANSACTION_COLUMNS = [
    "Stock group",
    "Stock class",
    "Transaction type",
    "Quantity",
    "Average liveweight (kg/hd)",
    "Source",
    "Merino sheep purchased (head)",
    "Code name",
]

# Physical column order of the season blocks on "Annual Data - Breed". The
# extractors look these up by name, so this order is independent of
# constant.SEASONS -- which is why those two functions are immune to the
# positional season mix-up that affects extract_seasonal_row_data.
BREED_SEASONS = ("Autumn", "Spring", "Summer", "Winter")

BREED_COLUMNS = (
    ["Stock group"]
    + [f"Proportion of ewes lambing/cows calving {s}" for s in BREED_SEASONS]
    + [f"Proportion of ewes/heifers lactating {s}" for s in BREED_SEASONS]
    + [f"Lambs/Calfs marking Rate {s}" for s in BREED_SEASONS]
)


def transaction_row(
    stock_group="sheep groupa",
    code_name="breedingEwes",
    transaction_type="Sale",
    quantity=0,
    liveweight=0,
    source=None,
    merino_head=0,
):
    """Build a "Transaction" sheet row dict."""
    return {
        "Stock group": stock_group,
        "Stock class": code_name,
        "Transaction type": transaction_type,
        "Quantity": quantity,
        "Average liveweight (kg/hd)": liveweight,
        "Source": source,
        "Merino sheep purchased (head)": merino_head,
        "Code name": code_name,
    }


def breed_row(
    stock_group="Sheep GroupA",
    lambing=(0, 0, 0, 0),
    lactating=(0, 0, 0, 0),
    marking=(0, 0, 0, 0),
):
    """Build an "Annual Data - Breed" row dict.

    Each 4-tuple is ordered by BREED_SEASONS (Autumn, Spring, Summer, Winter),
    matching the sheet's physical layout. "Stock group" stands in for the real
    sheet's blank first header, which the extractors index positionally.
    """
    row = {"Stock group": stock_group}
    for season, lamb, lact, mark in zip(BREED_SEASONS, lambing, lactating, marking):
        row[f"Proportion of ewes lambing/cows calving {season}"] = lamb
        row[f"Proportion of ewes/heifers lactating {season}"] = lact
        row[f"Lambs/Calfs marking Rate {season}"] = mark
    return row


@pytest.fixture
def input_xlsx_factory(tmp_path):
    """Write a temp .xlsx standing in for input/*.xlsm.

    All four pandas-read sheets are always written, empty unless rows are
    supplied. They have to travel together: every read_sheet call glob-resolves
    the same single file and reads a different sheet from it, so a workbook
    missing one of these raises "Worksheet named '<sheet>' not found" the
    moment anything tries to read it.

    seasonal/annual rows are seasonal_row()/annual_row() pd.Series, so an empty
    call still yields a valid (columnless) sheet -- extract_seasonal_data and
    extract_annual_data never touch a column unless a row is actually present
    to iterate over.
    """
    counter = itertools.count(1)

    def _factory(transactions=None, breeds=None, seasonal=None, annual=None):
        # A fresh filename per call keeps any path-keyed caching in the source
        # from serving one call's DataFrame to the next.
        path = tmp_path / f"input_{next(counter)}.xlsx"
        with pd.ExcelWriter(path) as writer:
            pd.DataFrame(transactions or [], columns=TRANSACTION_COLUMNS).to_excel(
                writer, sheet_name="Transaction", index=False
            )
            pd.DataFrame(breeds or [], columns=BREED_COLUMNS).to_excel(
                writer, sheet_name="Annual Data - Breed", index=False
            )
            pd.DataFrame(seasonal or []).to_excel(
                writer, sheet_name="Seasonal Data", index=False
            )
            pd.DataFrame(annual or []).to_excel(
                writer, sheet_name="Annual Data - Enterprise", index=False
            )
        return path

    return _factory


@pytest.fixture
def transaction_xlsx_factory(input_xlsx_factory):
    """Transaction-rows-only wrapper around input_xlsx_factory."""

    def _factory(rows: list[dict]):
        return input_xlsx_factory(transactions=rows)

    return _factory


@pytest.fixture
def mock_transaction_glob(monkeypatch):
    """Point the source's glob.glob at a temp workbook.

    This patches the glob module attribute, which works only because the source
    does `import glob` and calls `glob.glob(...)` at call time. If that ever
    becomes `from glob import glob`, a cached module-level path, or an injected
    argument, this mock stops applying SILENTLY and the tests begin reading the
    real gitignored input/*.xlsm instead. Change both sides together.
    """

    def _mock(xlsx_path):
        monkeypatch.setattr("glob.glob", lambda *_a, **_k: [str(xlsx_path)])

    return _mock


@pytest.fixture
def sheep_factory():
    def _factory(groups=1, ids=None):
        return Sheep(groups, ids)

    return _factory


@pytest.fixture
def beef_factory():
    def _factory(groups=1, ids=None):
        return Beef(groups, ids)

    return _factory
