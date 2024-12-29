from datetime import datetime
from pathlib import Path
import time
from urllib.parse import urlparse, parse_qs, urljoin

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


URL = "https://victoryfund.org/our-candidates/"


def extract(page_source, **additional_info):

    soup = BeautifulSoup(page_source, "html.parser")

    extracted = []

    cards = soup.select("li.candidate div.details-wrap")

    for card in cards:
        name = card.select_one("h4.candidate-name")
        office = card.select_one("div.position")
        location = card.select_one("div.location")

        extracted.append(
            {
                "name": name.get_text(strip=True),
                "office": office.get_text(strip=True),
                "location": location.get_text(strip=True),
            }
        )

    return extracted


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

    select_office = chrome_driver.find_elements(
        By.CSS_SELECTOR, "div.filter-office_level li.has-items > a"
    )
    office_to_get = ("Federal", "Governor", "Statewide", "State Legislature")

    params = set()

    for a in select_office:
        if a.get_attribute("title") in office_to_get:
            url = urlparse(a.get_attribute("href"))
            query_params = parse_qs(url.query)
            params.add(query_params.get("office_level").pop())

    URL_w_params = urljoin(URL, f"?office_level={",".join(params)}")

    chrome_driver.get(URL_w_params)

    time.sleep(3)

    while True:

        current_height = chrome_driver.execute_script(
            "return document.body.scrollHeight"
        )

        chrome_driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        time.sleep(2)

        loaded_height = chrome_driver.execute_script(
            "return document.body.scrollHeight"
        )

        if loaded_height > current_height:
            continue
        else:
            break

    save_html(
        chrome_driver.page_source,
        export_path / "HTML_FILES",
        filename,
    )

    extracted = extract(chrome_driver.page_source)
    records_extracted = dict(enumerate(extracted))

    return records_extracted
