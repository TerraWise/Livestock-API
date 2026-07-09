from copy import deepcopy

from internal.sheep_vars import sheep_stock_classes, sheep_annual_stock_class_data
from internal.beef_vars import beef_stock_classes, beef_annual_stock_class_data
from internal.inv_extraction import extract_inventories_from_excel, extract_annual_data

# Seasonal list
seasons = ["autumn", "winter", "spring", "summer"]

# Annual stock class data template per species
annual_stock_class_data = {
    "sheep": sheep_annual_stock_class_data,
    "beef": beef_annual_stock_class_data,
}


class Livestock:
    def __init__(
        self,
        species: str,
        stock_classes: list[str],
        groups: int = 1,
        ids: list[str] | None = None,
    ):
        if ids is not None:
            if groups != len(ids):
                raise ValueError(
                    "Number of groups must match the number of IDs provided."
                )

        self.species = species
        self.stock_classes = stock_classes

        # Create stock class data structure
        self.metadata = {self.species: []}
        for g in range(groups):
            self.metadata[self.species].append(
                {
                    "id": ids[g] if ids else "",
                    "classes": {},
                }
            )

    def seasonal_data(
        self,
        stock_class: str,
        season: str,
        head: int,
        liveweight: float,
        liveweightGain: float,
        crudeProtein: float = 0,
        dryMatterDigestibility: float = 0,
        index: int = 0,
    ):
        target = self.metadata[self.species][index]["classes"][stock_class][season]

        target.update(
            {
                "head": head,
                "liveweight": liveweight,
                "liveweightGain": liveweightGain,
            }
        )

        for key, value in (
            ("crudeProtein", crudeProtein),
            ("dryMatterDigestibility", dryMatterDigestibility),
        ):
            if value > 0:
                target[key] = value

    def stock_class_data(self, group: int, seasonal_beef: list):
        for i in range(group):
            for stock_class in self.stock_classes:
                self.metadata[self.species][i]["classes"][stock_class] = deepcopy(
                    annual_stock_class_data[self.species]
                )
                self.metadata[self.species][i]["classes"][stock_class]["purchases"] = (
                    seasonal_beef[i][stock_class]["purchases"]
                )
                for season in seasons:
                    seasonal_beef_data = seasonal_beef[i][stock_class][season]

                    self.seasonal_data(
                        stock_class, season, **seasonal_beef_data, index=i
                    )


class Sheep(Livestock):
    def __init__(self, group: int = 1):
        super().__init__("sheep", sheep_stock_classes, group)
        self.stock_classes = sheep_stock_classes


class Beef(Livestock):
    def __init__(self, group: int = 1):
        super().__init__("beef", beef_stock_classes, group)
        self.stock_classes = beef_stock_classes


def create_sheep_json_data(inventory_sheet, group: int = 1) -> dict:
    sheep = Sheep(group)
    seasonal_sheep = extract_inventories_from_excel(inventory_sheet, sheep.species)
    sheep.stock_class_data(group, seasonal_sheep)
    sheep.metadata = extract_annual_data(inventory_sheet, sheep.metadata, sheep.species)

    return sheep.metadata


def create_beef_json_data(inventory_sheet, group: int = 1) -> dict:
    beef = Beef(group)
    seasonal_beef = extract_inventories_from_excel(inventory_sheet, beef.species)
    beef.stock_class_data(group, seasonal_beef)
    beef.metadata = extract_annual_data(inventory_sheet, beef.metadata, beef.species)

    return beef.metadata
