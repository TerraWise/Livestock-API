import pytest

from internal.json_creation import agro_zone


def test_state_none_defaults_to_wa_sw():
    result = agro_zone(None)
    assert result == {
        "state": "wa_sw",
        "northOfTropicOfCapricorn": False,
        "rainfallAbove600": False,
    }


def test_state_none_still_echoes_flags():
    result = agro_zone(None, northOfTropicOfCapricorn=True, rainfallAbove600mm=True)
    assert result["state"] == "wa_sw"
    assert result["northOfTropicOfCapricorn"] is True
    assert result["rainfallAbove600"] is True


def test_empty_string_state():
    assert agro_zone("")["state"] == ""


def test_whitespace_only_state():
    assert agro_zone("   ")["state"] == ""


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("WA", "wa"),
        ("WA SW", "wa_sw"),
        ("  WA   SW  ", "wa_sw"),
        ("WA\tSW\n", "wa_sw"),
        ("wa\nsw", "wa_sw"),
    ],
)
def test_state_normalization(raw, expected):
    assert agro_zone(raw)["state"] == expected


@pytest.mark.parametrize("north", [True, False])
@pytest.mark.parametrize("rainfall", [True, False])
def test_flag_pass_through_and_key_rename(north, rainfall):
    result = agro_zone("WA SW", northOfTropicOfCapricorn=north, rainfallAbove600mm=rainfall)
    assert result["northOfTropicOfCapricorn"] is north
    assert result["rainfallAbove600"] is rainfall
    assert "rainfallAbove600mm" not in result


def test_exact_key_set_state_none():
    assert set(agro_zone(None).keys()) == {"state", "northOfTropicOfCapricorn", "rainfallAbove600"}


def test_exact_key_set_state_present():
    assert set(agro_zone("WA SW").keys()) == {"state", "northOfTropicOfCapricorn", "rainfallAbove600"}
