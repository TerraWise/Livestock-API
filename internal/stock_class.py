from copy import deepcopy

from internal.constant import (
    beef_stock_classes,
    sheep_stock_classes,
    annual_stock_class_data,
)
from internal.inv_extraction import extract_seasonal_data, extract_annual_data


class Livestock:
    def __init__(
        self,
        species: str,
        stock_classes: list[str],
        groups: int = 1,
        ids: list[str] | None = None,
    ):
        if not ids:
            ids = None
        if groups < 1:
            groups = 1

        if ids is not None:
            if groups != len(ids):
                raise ValueError(
                    "Number of groups must match the number of IDs provided."
                )

        self.species = species
        self.stock_classes = stock_classes
        self.ids = ids if ids else [""] * groups

        # Create stock class data structure
        self.metadata = {self.species: []}
        for g in range(groups):
            self.metadata[self.species].append(
                {
                    "id": ids[g] if ids else "",
                    "classes": {},
                }
            )

    def stock_class_data(self, seasonal_data: dict):
        species_data = seasonal_data.get(self.species, {})
        for i, id in enumerate(self.ids):
            stock_data = species_data.get(id)
            for stock_class in self.stock_classes:
                self.metadata[self.species][i]["classes"][stock_class] = deepcopy(
                    annual_stock_class_data[self.species]
                )
                if stock_data is None:
                    continue

                if stock_class in stock_data:
                    self.metadata[self.species][i]["classes"][stock_class].update(
                        stock_data[stock_class]
                    )


class Sheep(Livestock):
    def __init__(self, group: int = 1, ids: list[str] | None = None):
        super().__init__("sheep", sheep_stock_classes, group, ids=ids)


class Beef(Livestock):
    def __init__(self, group: int = 1, ids: list[str] | None = None):
        super().__init__("beef", beef_stock_classes, group, ids=ids)


LIVESTOCK_CLASSES = {"sheep": Sheep, "beef": Beef}


def create_json_data(
    species: str, group: int = 1, ids: list[str] | None = None
) -> dict:
    """Build one species' branch of the payload."""
    livestock = LIVESTOCK_CLASSES[species](group, ids)
    livestock.stock_class_data(extract_seasonal_data(species))
    livestock.metadata = extract_annual_data(livestock)

    return livestock.metadata


# Thin wrappers over create_json_data. Worth keeping: they bind one string and
# restate nothing, and they are what main.py and the tests already call.
def create_sheep_json_data(group: int = 1, ids: list[str] | None = None) -> dict:
    return create_json_data("sheep", group, ids)


def create_beef_json_data(group: int = 1, ids: list[str] | None = None) -> dict:
    return create_json_data("beef", group, ids)
