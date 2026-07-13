def agro_zone(
    state: str | None,
    northOfTropicOfCapricorn: bool = False,
    rainfallAbove600mm: bool = False,
) -> dict:
    if state is None:
        return {
            "state": "wa_sw",
            "northOfTropicOfCapricorn": northOfTropicOfCapricorn,
            "rainfallAbove600": rainfallAbove600mm,
        }
    return {
        "state": "_".join(state.lower().split()),
        "northOfTropicOfCapricorn": northOfTropicOfCapricorn,
        "rainfallAbove600": rainfallAbove600mm,
    }
