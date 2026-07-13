import pandas as pd
import pytest
from openpyxl import Workbook

from internal.stock_class import Beef, Sheep


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
    """Build a 31-element "Seasonal Data" row tuple (idx 0-30)."""
    row = [None] * 31
    row[0] = stock
    row[1] = stock_id
    row[3] = stock_class
    row[4:8] = head
    row[8:12] = liveweight
    row[12:16] = liveweight_gain
    row[16:20] = crude_protein
    row[20:24] = dry_matter_digestibility
    row[24:28] = feed_availability
    row[28] = head_shorn
    row[29] = wool_shorn
    row[30] = clean_wool_yield
    return tuple(row)


def annual_row(
    marker=1,
    id_value="GroupA",
    limestone=200,
    limestone_fraction=0.5,
    single_super=10,
    pasture_dryland=20,
    crops_dryland=30,
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
    repro_rates=(0, 0, 0, 0),
    seasonal_lambing=(0, 0, 0, 0),
):
    """Build a 48-element "Annual Data" row tuple (idx 0-47)."""
    row = [None] * 48
    row[0] = marker
    row[2] = id_value
    row[3] = limestone
    row[4] = limestone_fraction
    row[5] = single_super
    row[6] = pasture_dryland
    row[7] = crops_dryland
    row[8:22] = other_ferts
    row[22] = diesel
    row[23] = petrol
    row[24] = lpg
    row[25:31] = mineral
    row[31] = electricity_source
    row[32] = electricity_renewable
    row[33] = electricity_use
    row[34] = grain_feed
    row[35] = hay_feed
    row[36] = cottonseed_feed
    row[37] = herbicide
    row[38] = herbicide_other
    row[39:43] = repro_rates
    row[43:47] = seasonal_lambing
    return tuple(row)


def burning_row(
    fuel="coarse",
    season="early dry season",
    patchiness="high",
    rainfall_zone="low",
    years_since_last_fire=0,
    fire_scar_area=10,
    vegetation="Melaleuca woodland",
):
    """Build a 7-element "🔥Burning" row tuple (columns A-G)."""
    return (fuel, season, patchiness, rainfall_zone, years_since_last_fire, fire_scar_area, vegetation)


def veg_row(
    region="South West",
    tree_species="Mixed species (Environmental Plantings)",
    soil="Loams & Clays",
    area=50,
    age=5,
):
    """Build an 8-element "🌿 Vegetation" row tuple (columns A-H).

    extract_veg_data reads min_col=2, so column A (index 0 here) is a
    required-but-unused placeholder.
    """
    return (None, region, tree_species, None, soil, area, None, age)


@pytest.fixture
def transaction_xlsx_factory(tmp_path):
    columns = [
        "Stock group",
        "Stock class",
        "Head",
        "Average liveweight (kg)",
        "Transaction type",
        "Source",
        "Merino sheep purchased (head)",
    ]

    def _factory(rows: list[dict]):
        df = pd.DataFrame(rows, columns=columns)
        path = tmp_path / "transactions.xlsx"
        df.to_excel(path, sheet_name="Transaction", index=False)
        return path

    return _factory


@pytest.fixture
def mock_transaction_glob(monkeypatch):
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
