from internal.stock_class import create_sheep_json_data
from internal.inv_extraction import extract_inventories_from_excel, extract_annual_data
import os, openpyxl, glob, json, tempfile
import requests as rq


def main():
    file_path = glob.glob(os.path.join("input", "*.xlsx"))

    inventory_sheet = openpyxl.load_workbook(file_path[0], data_only=True)
    state = inventory_sheet["Client detail"].cell(17, 7).value

    json_data = create_sheep_json_data(
        inventory_sheet,
        state="_".join(state.lower().split()),
        northOfTropicOfCapricorn=False,
        rainfallAbove600mm=False,
    )

    json_data = extract_annual_data(inventory_sheet, json_data, "sheep")

    header = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "terrawise",
    }
    url = (
        "https://emissionscalculator-mtls.production.aiaapi.com/calculator/v3.0.0/sheep"
    )

    # Key and PEM file paths
    key = os.path.join("secret", "carbon-calculator-integration.key")
    pem = os.path.join("secret", "aiaghg-terrawise.pem")

    # Send the request
    response = rq.post(url, headers=header, data=json.dumps(json_data), cert=(pem, key))

    if response.status_code > 299:
        print(f"Error: {response.status_code}")
        with open(os.path.join("output", "error.json"), "w") as f:
            f.write(json.dumps(response.json(), indent=4))
            f.close()
        return

    with open(os.path.join("output", "response.json"), "w") as f:
        f.write(json.dumps(response.json(), indent=4))
        f.close()

    with open(os.path.join("input", "input.json"), "w") as f:
        f.write(json.dumps(json_data, indent=4))
        f.close()


if __name__ == "__main__":
    main()
