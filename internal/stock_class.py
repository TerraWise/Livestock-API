from copy import deepcopy

from internal.sheep_vars import (
    sheep_stock_classes,
    sheep_annual_stock_class_data,
)
from internal.json_creation import agro_zone

# Seasonal list
seasons = ["autumn", "winter", "spring", "summer"]


class Livestock:
    def __init__(self, species: str, group: int = 1, **kwargs):
        self.species = species

        self.metadata = agro_zone(
            kwargs["northOfTropicOfCapricorn"], kwargs["rainfallAbove600mm"]
        )
        # Create stock class data structure
        self.metadata[self.species] = [{"classes": {}}] * group


class Sheep(Livestock):
    def __init__(self, group: int = 1, **kwargs):
        super().__init__("sheep", group, **kwargs)
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


def create_sheep_json_data(seasonal_sheep: list, group: int = 1, **kwargs) -> dict:
    sheep = Sheep(group, **kwargs)
    sheep.stock_class_data(group, seasonal_sheep)

    return sheep.metadata
