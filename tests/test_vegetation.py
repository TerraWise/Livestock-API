from internal.vegetation import extract_veg_data, vegetation_planting

from tests.conftest import make_workbook, veg_row


def test_vegetation_planting_defaults():
    assert vegetation_planting() == {
        "beefProportion": [0],
        "sheepProportion": [0],
        "vegetation": {
            "age": 0,
            "area": 0,
            "region": "South West",
            "soil": "Loams & Clays",
            "treeSpecies": "Mixed species (Environmental Plantings)",
        },
    }


def test_vegetation_planting_custom_values():
    result = vegetation_planting(
        beef_proportion=[1],
        sheep_proportion=[0],
        age=10,
        area=25,
        region="South East",
        soil="Sandy Duplexes",
        tree_species="Native regeneration",
    )
    assert result == {
        "beefProportion": [1],
        "sheepProportion": [0],
        "vegetation": {
            "age": 10,
            "area": 25,
            "region": "South East",
            "soil": "Sandy Duplexes",
            "treeSpecies": "Native regeneration",
        },
    }


def test_vegetation_planting_default_lists_are_independent_per_call():
    # Regression test: beef_proportion/sheep_proportion now default to None
    # and get a fresh [0] built per call, so separate calls no longer share
    # (and can no longer cross-contaminate) the same list object.
    first = vegetation_planting()
    second = vegetation_planting()
    assert first["beefProportion"] is not second["beefProportion"]
    first["beefProportion"].append(999)
    assert first["beefProportion"] == [0, 999]
    assert second["beefProportion"] == [0]


def test_extract_veg_data_happy_path_two_complete_rows():
    wb = make_workbook(
        {
            "🌿 Vegetation": [
                veg_row(region="South West", area=52, age=6),
                veg_row(region="South East", area=174, age=30),
            ]
        }
    )
    result = extract_veg_data(wb)
    assert result == {
        "vegetation": [
            vegetation_planting(region="South West", area=52, age=6),
            vegetation_planting(region="South East", area=174, age=30),
        ]
    }


def test_extract_veg_data_row_zero_incomplete_yields_empty_list():
    incomplete = veg_row()[:-1] + (None,)  # age missing
    wb = make_workbook({"🌿 Vegetation": [incomplete]})
    result = extract_veg_data(wb)
    assert result == {"vegetation": []}


def test_extract_veg_data_later_row_incomplete_stops_without_a_default():
    complete = veg_row(region="South West", area=52, age=6)
    incomplete = veg_row()[:-1] + (None,)
    wb = make_workbook({"🌿 Vegetation": [complete, incomplete]})
    result = extract_veg_data(wb)
    assert result == {"vegetation": [vegetation_planting(region="South West", area=52, age=6)]}


def test_extract_veg_data_truly_empty_sheet_yields_empty_list():
    wb = make_workbook({"🌿 Vegetation": []})
    result = extract_veg_data(wb)
    assert result == {"vegetation": []}
