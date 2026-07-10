from openpyxl import Workbook


def vegetation_planting(
    beef_proportion: list[float] = [0],
    sheep_proportion: list[float] = [0],
    age: int = 0,
    area: float = 0,
    region: str = "South West",
    soil: str = "Loams & Clays",
    tree_species: str = "Mixed species (Environmental Plantings)",
) -> dict:
    return {
        "beefProportion": beef_proportion,
        "sheepProportion": sheep_proportion,
        "vegetation": {
            "age": age,
            "area": area,
            "region": region,
            "soil": soil,
            "treeSpecies": tree_species,
        },
    }


def extract_veg_data(inventory_sheet: Workbook) -> dict:
    ws = inventory_sheet["🌿 Vegetation"]
    veg_data = {"vegetation": []}

    for i, row in enumerate(
        ws.iter_rows(min_row=2, min_col=2, max_col=8, values_only=True)
    ):
        region, tree_species, _, soil, area, _, age = row

        if any(value is None for value in (region, tree_species, soil, area, age)):
            if i == 0:
                veg_data["vegetation"].append(vegetation_planting())
            break

        veg_data["vegetation"].append(
            vegetation_planting(
                age=age,
                area=area,
                region=region,
                soil=soil,
                tree_species=tree_species,
            )
        )

    return veg_data
