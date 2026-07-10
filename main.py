import os
import pandas as pd
import openpyxl
import glob
import json
import requests as rq

from internal.stock_class import create_sheep_json_data, create_beef_json_data
from internal.json_creation import agro_zone
from internal.burning import extract_burning_data
from internal.vegetation import extract_veg_data


def main():
    file_path = glob.glob(os.path.join("input", "*.xlsx"))

    inventory_sheet = openpyxl.load_workbook(file_path[0], data_only=True)
    state = inventory_sheet["👤Client detail"].cell(17, 7).value

    sheep_species_ids = []
    cattle_species_ids = []
    stock_info = pd.read_excel(file_path[0], "Stock information")
    for _, r in stock_info.iterrows():
        if r["Stock category"] == "Sheep":
            sheep_species_ids.append(r["ID"])
        elif r["Stock category"] == "Cattle":
            cattle_species_ids.append(r["ID"])

    region_data = agro_zone(state, False, False)
    sheep_data = create_sheep_json_data(
        inventory_sheet, len(sheep_species_ids), sheep_species_ids
    )
    beef_data = create_beef_json_data(
        inventory_sheet, len(cattle_species_ids), cattle_species_ids
    )
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
        response_body = response.json()
        error_detail = response_body.get("error")
        if isinstance(error_detail, str):
            try:
                response_body["error"] = json.loads(error_detail)
            except json.JSONDecodeError:
                pass

        error_log = {
            "statusCode": response.status_code,
            "url": url,
            "response": response_body,
            "requestPayload": json_data,
        }
        with open(os.path.join("log", "error.json"), "w") as f:
            json.dump(error_log, f, indent=4)
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
