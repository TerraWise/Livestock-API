from internal.burning import burning_record, extract_burning_data

from tests.conftest import burning_row, make_workbook


def test_burning_record_defaults():
    assert burning_record() == {
        "fireScarArea": 0,
        "fuel": "coarse",
        "patchiness": "high",
        "rainfallZone": "low",
        "season": "early dry season",
        "vegetation": "Melaleuca woodland",
        "yearsSinceLastFire": 0,
    }


def test_burning_record_custom_values():
    result = burning_record(
        fire_scar_area=25,
        fuel="fine",
        patchines="low",
        rainfall_zone="high",
        season="late dry season",
        vegetation="Eucalypt woodland",
        years_since_last_fire=3,
    )
    assert result == {
        "fireScarArea": 25,
        "fuel": "fine",
        "patchiness": "low",
        "rainfallZone": "high",
        "season": "late dry season",
        "vegetation": "Eucalypt woodland",
        "yearsSinceLastFire": 3,
    }


def test_extract_burning_data_happy_path_two_complete_rows():
    wb = make_workbook(
        {
            "🔥Savannah burning": [
                burning_row(fuel="coarse", fire_scar_area=10),
                burning_row(fuel="fine", fire_scar_area=20),
            ]
        }
    )
    result = extract_burning_data(wb)
    assert result == {
        "burning": [
            burning_record(fuel="coarse", fire_scar_area=10),
            burning_record(fuel="fine", fire_scar_area=20),
        ]
    }


def test_extract_burning_data_row_zero_incomplete_yields_empty_list():
    incomplete = burning_row()[:-1] + (None,)  # vegetation missing
    wb = make_workbook({"🔥Savannah burning": [incomplete]})
    result = extract_burning_data(wb)
    assert result == {"burning": []}


def test_extract_burning_data_later_row_incomplete_stops_without_a_default():
    complete = burning_row(fuel="coarse", fire_scar_area=10)
    incomplete = burning_row()[:-1] + (None,)
    wb = make_workbook({"🔥Savannah burning": [complete, incomplete]})
    result = extract_burning_data(wb)
    assert result == {"burning": [burning_record(fuel="coarse", fire_scar_area=10)]}


def test_extract_burning_data_row_zero_all_none_yields_empty_list():
    all_none = (None,) * 7
    wb = make_workbook({"🔥Savannah burning": [all_none]})
    result = extract_burning_data(wb)
    assert result == {"burning": []}


def test_extract_burning_data_truly_empty_sheet_yields_empty_list():
    # No data rows at all past the placeholder row 1 -> iter_rows(min_row=2, ...)
    # yields zero rows, so the loop body never runs. Same net result ({"burning": []})
    # as an incomplete row 0, now that the row-0-only default record was removed.
    wb = make_workbook({"🔥Savannah burning": []})
    result = extract_burning_data(wb)
    assert result == {"burning": []}
