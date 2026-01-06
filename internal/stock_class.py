from copy import deepcopy

from internal.sheep_vars import (
    sheep_stock_classes,
    sheep_annual_stock_class_data,
)
from internal.beef_vars import beef_stock_classes, beef_annual_stock_class_data
from internal.inv_extraction import extract_inventories_from_excel, extract_annual_data

# Seasonal list
seasons = ["autumn", "winter", "spring", "summer"]


class Livestock:
    def __init__(self, species: str, group: int = 1):
        self.species = species

        # Create stock class data structure
        self.metadata = {}
        self.metadata[self.species] = [{"classes": {}}] * group


class Sheep(Livestock):
    def __init__(self, group: int = 1):
        super().__init__("sheep", group)
        self.stock_classes = sheep_stock_classes

    def seasonal_data(
        self,
        stock_class: str,
        season: str,
        head: int,
        liveweight: float,
        liveweightGain: float,
        crudeProtein: float = 0,
        dryMatterDigestibility: float = 0,
        feedAvailability: float = 0,
        index: int = 0,
    ):
        target = self.metadata["sheep"][index]["classes"][stock_class][season]

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
            ("feedAvailability", feedAvailability),
        ):
            if value > 0:
                target[key] = value

    def stock_class_data(self, group: int, seasonal_sheep: list):
        for i in range(group):
            for stock_class in self.stock_classes:
                self.metadata["sheep"][i]["classes"][stock_class] = deepcopy(
                    sheep_annual_stock_class_data
                )
                self.metadata["sheep"][i]["classes"][stock_class]["purchases"] = (
                    seasonal_sheep[i][stock_class]["purchases"]
                )
                for season in seasons:
                    seasonal_sheep_data = seasonal_sheep[i][stock_class][season]

                    self.seasonal_data(
                        stock_class, season, **seasonal_sheep_data, index=i
                    )


class Beef(Livestock):
    def __init__(self, group: int = 1, **kwargs):
        super().__init__("beef", group, **kwargs)
        self.stock_classes = beef_stock_classes

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
        target = self.metadata["beef"][index]["classes"][stock_class][season]

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
                self.metadata["beef"][i]["classes"][stock_class] = deepcopy(
                    beef_annual_stock_class_data
                )
                self.metadata["beef"][i]["classes"][stock_class]["purchases"] = (
                    seasonal_beef[i][stock_class]["purchases"]
                )
                for season in seasons:
                    seasonal_beef_data = seasonal_beef[i][stock_class][season]

                    self.seasonal_data(
                        stock_class, season, **seasonal_beef_data, index=i
                    )


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
