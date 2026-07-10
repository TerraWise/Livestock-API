from openpyxl import Workbook


def burning_record(
    fire_scar_area: float = 0,
    fuel: str = "coarse",
    patchines: str = "high",
    rainfall_zone: str = "low",
    season: str = "early dry season",
    vegetation: str = "Melaleuca woodland",
    years_since_last_fire: int = 0,
) -> dict:
    return {
        "fireScarArea": fire_scar_area,
        "fuel": fuel,
        "patchiness": patchines,
        "rainfallZone": rainfall_zone,
        "season": season,
        "vegetation": vegetation,
        "yearsSinceLastFire": years_since_last_fire,
    }


def extract_burning_data(inventory_sheet: Workbook) -> dict:
    ws = inventory_sheet["🔥Burning"]
    burning_data = {"burning": []}

    for i, row in enumerate(
        ws.iter_rows(min_row=2, min_col=1, max_col=7, values_only=True)
    ):
        fuel, season, patchiness, rainfall_zone, years_since_last_fire, fire_scar_area, vegetation = row

        if any(value is None for value in row):
            if i == 0:
                burning_data["burning"].append(burning_record())
            break

        burning_data["burning"].append(
            burning_record(
                fire_scar_area=fire_scar_area,
                fuel=fuel,
                patchines=patchiness,
                rainfall_zone=rainfall_zone,
                season=season,
                vegetation=vegetation,
                years_since_last_fire=years_since_last_fire,
            )
        )

    return burning_data
