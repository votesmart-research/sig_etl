from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException

from tqdm import tqdm


URL = "https://scorecard.afscme.org"


def get_state_urls(page_source):
    soup = BeautifulSoup(page_source, "html.parser")
    select_states = soup.find("select", {"id": "change-state"})
    return [f"state.html?s={o['id']}" for o in select_states.find_all("option")[1:]]


def extract(page_source, **additional_info):

    soup = BeautifulSoup(page_source, "html.parser")

    offices = soup.find_all("h2", {"class": "card-grouping-headline"})
    tables = soup.find_all("table", {"class": "state-table"})

    def extract_table(table, office):

        headers = ["Name"] + [
            th.get_text(strip=True) for th in table.find_all("th")[1:]
        ]
        rows = [tr.find_all("td") for tr in table.find_all("tr")]

        def get_text(x):
            return x.get_text(strip=True)

        return [
            dict(zip(headers, map(get_text, row)))
            | {"office": office}
            | additional_info
            for row in rows[2:]
        ]

    extracted = []

    for office, table in zip(offices, tables):
        office_text = office.get_text(strip=True)
        extracted += extract_table(table, office_text)

    return extracted


def extract_files(files: list):

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

    filepath = filepath / "HTML_FILES"
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


def main(filename: str, export_path: Path, html_path: Path = None):

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
    chrome_options.add_argument("headless")
    chrome_driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    chrome_driver.get(URL)

    # close overlay
    ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

    extracted = []

    for state_url in tqdm(get_state_urls(chrome_driver.page_source)):
        chrome_driver.get(urljoin(URL, state_url))
        extracted += extract(chrome_driver.page_source)
        save_html(
            chrome_driver.page_source,
            export_path / "HTML_FILES",
            filename,
            state_url.split("=")[-1],
        )

    extracted = [d for d in extracted if d.get("Name")]

    records_extracted = dict(enumerate(extracted))
    return records_extracted
