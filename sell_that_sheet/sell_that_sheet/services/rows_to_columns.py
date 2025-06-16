import pandas as pd
from tqdm import tqdm
import logging

logger = logging.getLogger(__name__)

def rows_to_columns(input_path: str, xlsx_path: str) -> None:
    """Convert a row based data file into a column oriented XLSX file.

    Parameters
    ----------
    input_path : str
        Path to the source row based file (semicolon separated).
    xlsx_path : str
        Path where the XLSX file will be saved.
    """
    with open(input_path, "r", encoding="utf-8") as file:
        lines = file.readlines()

    # Skip the header line
    lines = lines[1:]

    products = []
    product = {}

    logger.info("Processing rows to convert to columns...")

    for line in tqdm(lines):
        if ";" not in line:
            if product:
                products.append(product)
            product = {"id": line.strip()}
            continue

        line = line.strip().split(";")
        if len(line) > 1:
            product[line[0]] = line[1]

    logger.info("Finalizing product data...")

    if product:
        products.append(product)

    logger.info(f"Total products processed: {len(products)}")
    df = pd.DataFrame(products)
    cols = df.columns.tolist()
    cols.sort(key=lambda x: df[x].count(), reverse=True)
    df = df[cols]
    logger.info("Saving DataFrame to XLSX file...")
    df.to_excel(xlsx_path, index=False)
    logger.info(f"Data saved to {xlsx_path} successfully.")
