from copy import deepcopy

import pytest

from internal.constant import (
    beef_annual_stock_class_data,
    beef_stock_classes,
    sheep_stock_classes,
)
from internal.stock_class import (
    Beef,
    Sheep,
    create_beef_json_data,
    create_sheep_json_data,
)

from tests.conftest import (
    CATTLE_ENTERPRISE,
    SHEEP_ENTERPRISE,
    annual_row,
    breed_row,
    seasonal_row,
)


class TestLivestockInit:
    def test_ids_length_mismatch_raises_value_error(self, beef_factory):
        with pytest.raises(
            ValueError, match="Number of groups must match the number of IDs provided."
        ):
            beef_factory(groups=2, ids=["OnlyOne"])

    def test_ids_none_defaults_to_empty_strings_and_blank_metadata(self):
        livestock = Beef(3)
        assert livestock.ids == ["", "", ""]
        assert livestock.metadata == {
            "beef": [
                {"id": "", "classes": {}},
                {"id": "", "classes": {}},
                {"id": "", "classes": {}},
            ]
        }

    def test_zero_groups_with_empty_ids_defaults_to_one_placeholder_group(
        self, beef_factory
    ):
        livestock = beef_factory(groups=0, ids=[])
        assert livestock.ids == [""]
        assert livestock.metadata == {"beef": [{"id": "", "classes": {}}]}

    def test_sheep_wires_correct_species_and_stock_classes(self):
        sheep = Sheep()
        assert sheep.species == "sheep"
        assert sheep.stock_classes == sheep_stock_classes

    def test_beef_wires_correct_species_and_stock_classes(self):
        beef = Beef()
        assert beef.species == "beef"
        assert beef.stock_classes == beef_stock_classes


class TestStockClassData:
    def test_overlay_applied_when_stock_class_present(self, beef_factory):
        livestock = beef_factory(groups=1, ids=["GroupA"])
        seasonal_data = {
            "beef": {
                "GroupA": {
                    "cowsGt2": {
                        "autumn": {"head": 50, "liveweight": 1, "liveweightGain": 0}
                    },
                }
            }
        }
        livestock.stock_class_data(seasonal_data)
        classes = livestock.metadata["beef"][0]["classes"]
        assert classes["cowsGt2"]["autumn"]["head"] == 50
        # stock classes with no overlay data stay at template defaults
        assert classes["bullsGt1"]["autumn"]["head"] == 0

    def test_missing_stock_class_for_present_id_keeps_template_no_crash(
        self, beef_factory
    ):
        livestock = beef_factory(groups=1, ids=["GroupA"])
        seasonal_data = {"beef": {"GroupA": {}}}
        livestock.stock_class_data(seasonal_data)
        assert (
            livestock.metadata["beef"][0]["classes"]["cowsGt2"]["autumn"]["head"] == 0
        )

    def test_missing_id_entirely_keeps_all_template_defaults(self, beef_factory):
        livestock = beef_factory(groups=1, ids=["GroupA"])
        seasonal_data = {"beef": {}}
        livestock.stock_class_data(seasonal_data)
        assert livestock.metadata["beef"][0]["classes"]["cowsGt2"] == deepcopy(
            beef_annual_stock_class_data
        )

    def test_dairy_origin_default_survives_without_purchases_overlay(
        self, beef_factory
    ):
        livestock = beef_factory(groups=1, ids=["GroupA"])
        seasonal_data = {
            "beef": {
                "GroupA": {
                    "cowsGt2": {
                        "autumn": {"head": 10, "liveweight": 1, "liveweightGain": 0}
                    },
                }
            }
        }
        livestock.stock_class_data(seasonal_data)
        purchases = livestock.metadata["beef"][0]["classes"]["cowsGt2"]["purchases"]
        assert purchases[0]["purchaseSource"] == "Dairy origin"

    def test_purchases_overlay_from_empty_fallback_still_reads_dairy_origin(
        self, beef_factory
    ):
        # Mirrors exactly what extract_transaction_data's empty-match fallback
        # now produces (build_purchase_entry's own default source is "Dairy
        # origin"), so the overlay agrees with the template instead of
        # silently overwriting it with an empty string.
        livestock = beef_factory(groups=1, ids=["GroupA"])
        seasonal_data = {
            "beef": {
                "GroupA": {
                    "cowsGt2": {
                        "purchases": [
                            {
                                "head": 0,
                                "purchaseWeight": 0,
                                "purchaseSource": "Dairy origin",
                            }
                        ]
                    },
                }
            }
        }
        livestock.stock_class_data(seasonal_data)
        purchases = livestock.metadata["beef"][0]["classes"]["cowsGt2"]["purchases"]
        assert purchases[0]["purchaseSource"] == "Dairy origin"

    def test_real_purchase_source_overrides_dairy_origin_default(self, beef_factory):
        livestock = beef_factory(groups=1, ids=["GroupA"])
        seasonal_data = {
            "beef": {
                "GroupA": {
                    "cowsGt2": {
                        "purchases": [
                            {
                                "head": 10,
                                "purchaseWeight": 300,
                                "purchaseSource": "sw WA",
                            }
                        ]
                    },
                }
            }
        }
        livestock.stock_class_data(seasonal_data)
        purchases = livestock.metadata["beef"][0]["classes"]["cowsGt2"]["purchases"]
        assert purchases[0]["purchaseSource"] == "sw WA"


class TestCreateJsonDataEndToEnd:
    """End-to-end shape, mirroring how main.py builds its id lists.

    Group 0 is always the enterprise pseudo-group -- it is the only id that
    appears in "Annual Data - Enterprise", so it is the group annual figures
    land on. Breed groups follow, and they are the ones that carry seasonal
    stock-class rows. No group has both.
    """

    def test_create_beef_json_data(
        self, mock_transaction_glob, input_xlsx_factory
    ):
        mock_transaction_glob(
            input_xlsx_factory(
                seasonal=[
                    seasonal_row(
                        stock="beef",
                        stock_id="Angus",
                        stock_class="cowsGt2",
                        head=(50, 50, 50, 50),
                    ),
                ],
                annual=[annual_row(stock_cat=CATTLE_ENTERPRISE, diesel=1000)],
            )
        )
        result = create_beef_json_data(group=2, ids=[CATTLE_ENTERPRISE, "Angus"])

        enterprise, breed = result["beef"]
        assert enterprise["id"] == CATTLE_ENTERPRISE
        assert enterprise["diesel"] == 1000

        assert breed["id"] == "Angus"
        assert set(breed["classes"].keys()) == set(beef_stock_classes)
        assert breed["classes"]["cowsGt2"]["autumn"]["head"] == 50
        # No Annual Data row of its own, so annual fields keep their defaults.
        assert breed["diesel"] == 0

        for entry in result["beef"]:
            assert "cowsCalving" in entry
            assert "seasonalLambing" not in entry
            assert "merinoPercent" not in entry

    def test_create_sheep_json_data(self, mock_transaction_glob, input_xlsx_factory):
        # seasonalLambing reads the "Lambs/Calfs marking Rate" column (the
        # `marking=` argument here) -- see the AIA-shape note on
        # TestExtractLambingCalvingRate in test_inv_extraction.py for why it
        # doesn't share ewesLambing's column.
        mock_transaction_glob(
            input_xlsx_factory(
                seasonal=[
                    seasonal_row(
                        stock="sheep",
                        stock_id="Merino",
                        stock_class="breedingEwes",
                        head=(100, 100, 100, 100),
                        head_shorn=100,
                        wool_shorn=400,
                        clean_wool_yield=0.9,
                    ),
                ],
                annual=[annual_row(stock_cat=SHEEP_ENTERPRISE, diesel=500)],
                breeds=[breed_row(stock_group="Sheep Merino", marking=(1, 2, 3, 4))],
            )
        )
        result = create_sheep_json_data(group=2, ids=[SHEEP_ENTERPRISE, "Merino"])

        enterprise, breed = result["sheep"]
        assert enterprise["id"] == SHEEP_ENTERPRISE
        assert enterprise["diesel"] == 500

        assert breed["id"] == "Merino"
        assert set(breed["classes"].keys()) == set(sheep_stock_classes)
        assert breed["classes"]["breedingEwes"]["autumn"]["head"] == 100
        assert breed["classes"]["breedingEwes"]["headShorn"] == 100

        # Rate columns are matched by name, so the sheet's Autumn/Spring/Summer/
        # Winter layout maps onto SEASONS' autumn/winter/spring/summer order.
        assert breed["seasonalLambing"] == {
            "autumn": 1,
            "winter": 4,
            "spring": 2,
            "summer": 3,
        }
        for entry in result["sheep"]:
            assert "ewesLambing" in entry
            assert entry["merinoPercent"] == 0

    def test_multi_group_id_isolation_missing_annual_row_for_one_group(
        self, mock_transaction_glob, input_xlsx_factory
    ):
        mock_transaction_glob(
            input_xlsx_factory(
                seasonal=[
                    seasonal_row(
                        stock="sheep", stock_id="Merino", stock_class="breedingEwes"
                    ),
                    seasonal_row(
                        stock="sheep", stock_id="XB", stock_class="breedingEwes"
                    ),
                ],
                annual=[annual_row(stock_cat=SHEEP_ENTERPRISE, diesel=750)],
            )
        )
        result = create_sheep_json_data(
            group=3, ids=[SHEEP_ENTERPRISE, "Merino", "XB"]
        )
        # Only the enterprise group has an Annual Data row, so only it gets the
        # row-derived figures.
        assert result["sheep"][0]["diesel"] == 750
        # The breed groups keep the zeroed defaults rather than being left
        # without the key at all -- and merinoPercent is computed per group,
        # independently of any Annual Data row, so every group still has it.
        for entry in result["sheep"][1:]:
            assert entry["diesel"] == 0
            assert entry["merinoPercent"] == 0
