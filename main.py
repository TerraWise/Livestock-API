import os
import openpyxl
import glob
import json
import requests as rq

from internal.stock_class import create_sheep_json_data, create_beef_json_data
from internal.json_creation import agro_zone
from internal.burning import extract_burning_data
from internal.vegetation import extract_veg_data

from pprint import pprint


def main():
    file_path = glob.glob(os.path.join("input", "*.xlsx"))

    inventory_sheet = openpyxl.load_workbook(file_path[0], data_only=True)
    state = inventory_sheet["Client detail"].cell(17, 7).value

    region_data = agro_zone("_".join(state.lower().split()), False, False)
    sheep_data = create_sheep_json_data(inventory_sheet, 1)
    beef_data = create_beef_json_data(inventory_sheet, 1)
    burning_data = extract_burning_data(inventory_sheet)
    veg_data = extract_veg_data(inventory_sheet)

    json_data = region_data | sheep_data | beef_data | burning_data | veg_data

    header = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "terrawise",
    }
    url = "https://emissionscalculator-mtls.production.aiaapi.com/calculator/v3.0.0/sheepbeef"

    # Key and PEM file paths
    key = os.path.join("secret", "carbon-calculator-integration.key")
    pem = os.path.join("secret", "aiaghg-terrawise.pem")

    # Send the request
    response = rq.post(url, headers=header, data=json.dumps(json_data), cert=(pem, key))

    if response.status_code > 299:
        print(f"Error: {response.status_code}")
        with open(os.path.join("log", "error.json"), "w") as f:
            f.write(json.dumps(response.json(), indent=4))
            f.close()
        print("Check log/error.json for more details")
        return

    with open(os.path.join("output", "response.json"), "w") as f:
        f.write(json.dumps(response.json(), indent=4))
        f.close()

    with open(os.path.join("input", "input.json"), "w") as f:
        f.write(json.dumps(json_data, indent=4))
        f.close()


if __name__ == "__main__":
    main()
