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


def create_sheep_json_data(
    inventory_sheet, group: int = 1, ids: list[str] | None = None
) -> dict:
    sheep = Sheep(group, ids)
    seasonal_sheep = extract_seasonal_data(inventory_sheet)
    sheep.stock_class_data(seasonal_sheep)
    sheep.metadata = extract_annual_data(inventory_sheet, sheep)

    return sheep.metadata


def create_beef_json_data(
    inventory_sheet, group: int = 1, ids: list[str] | None = None
) -> dict:
    beef = Beef(group, ids)
    seasonal_beef = extract_seasonal_data(inventory_sheet)
    beef.stock_class_data(seasonal_beef)
    beef.metadata = extract_annual_data(inventory_sheet, beef)

    return beef.metadata
