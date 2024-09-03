import re
import time
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.common.exceptions import NoSuchElementException


def extract(page_source, **additional_info):

    soup = BeautifulSoup(page_source, "html.parser")
    table = soup.find("table")

    def extract_table(table):

        headers = [th.get_text(strip=True) for th in table.thead.find_all("th")]
        rows = [tr.find_all("td") for tr in table.tbody.find_all("tr")]

        def get_text(x):
            return x.get_text(strip=True)

        return [
            dict(zip(headers, map(get_text, row))) | additional_info for row in rows
        ]

    return extract_table(table)


def extract_files(files: list[Path]):

    extracted = []

    for file in files:

        with open(file, "r") as f:
            extracted += extract(f.read())

    records_extracted = dict(enumerate(extracted))

    return records_extracted


def save_html(
    page_source,
    filepath: Path,
    filename: str,
    *additional_info,
):

    filepath.mkdir(exist_ok=True)

    soup = BeautifulSoup(page_source, "html.parser")
    timestamp = datetime.strftime(datetime.now(), "%Y-%m-%d-%H%M%S-%f")

    with open(
        filepath
        / (
            f"{filename}_{'-'.join(map(str, additional_info))}"
            f"{'-' if additional_info else ''}{timestamp}.html"
        ),
        "w",
    ) as f:
        f.write(str(soup))


def main(filename: str, export_path: Path, urls, html_path: Path = None):

    if html_path:
        html_files = filter(
            lambda f: f.name.endswith(".html"),
            (export_path / html_path).iterdir(),
        )
        records_extracted = extract_files(
            sorted(html_files, key=lambda x: x.stat().st_ctime)
        )
        return records_extracted

    chrome_service = Service()
    chrome_options = Options()
    chrome_options.add_argument("incognito")
    # chrome_options.add_argument("headless")
    chrome_driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    extracted = []

    for url in urls:
        chrome_driver.get(url)

        div = chrome_driver.find_element(By.CSS_SELECTOR, ".dataTables_info")
        items = list(re.finditer(r"\d+", div.text))
        max_entries = items[-1].group(0) if len(items) >= 3 else 200
    
        chrome_driver.execute_script(
            """
            select_el = document.querySelector("select")
            options = select_el.querySelectorAll("option")
            options[options.length - 1].value = arguments[0]
            """,
            max_entries,
        )

        select = Select(chrome_driver.find_element(By.CSS_SELECTOR, "select"))
        select.select_by_index(len(select.options) - 1)

        # close overlay
        ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

        save_html(
            chrome_driver.page_source,
            export_path / "HTML_FILES",
            filename,
        )

        extracted += extract(chrome_driver.page_source)

    records_extracted = dict(enumerate(extracted))

    return records_extracted
