def agro_zone(
    state: str = "wa_sw",
    northOfTropicOfCapricorn: bool = False,
    rainfallAbove600mm: bool = False,
) -> dict:
    return {
        "state": state,
        "northOfTropicOfCapricorn": northOfTropicOfCapricorn,
        "rainfallAbove600": rainfallAbove600mm,
    }
