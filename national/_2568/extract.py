from datetime import datetime
from pathlib import Path

import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait



URL = "https://endcitizensunited.org/scorecard/"


def extract(page_source, **additional_info):

    soup = BeautifulSoup(page_source, "html.parser")

    card_container = soup.select_one("div div:nth-child(2)")
    cards = card_container.find_all("div", recursive=False)

    extracted = []
    for card in cards:
        container = card.div.div
        divs = container.find_all("div", recursive=False)

        info = divs[0].get_text(" ", strip=True)
        grade = divs[1].get_text(" ", strip=True)

        extracted.append({"info": info, "grade": grade} | additional_info)

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

    # Allow the driver to return immediately without the DOM being loaded
    # Doing this allow the driver to inject some JS Script in
    chrome_options.page_load_strategy = "none"

    chrome_driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    # close overlay
    ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

    extracted = []

    chrome_driver.get(URL)

    # Inject JS Script to prevent shadowRoot from closing
    chrome_driver.execute_script(
        """
        Element.prototype._attachShadow = Element.prototype.attachShadow;
        Element.prototype.attachShadow = function () {
            return this._attachShadow({ mode: "open" });
        };
    """
    )

    WebDriverWait(chrome_driver, 10).until(
        EC.visibility_of_element_located((By.ID, "scorecardContainer"))
    )

    # When the page refreshes, the injection script could not run as fast as the
    # before the page loads, so it requires the manual clicking of elements.
    inputs = chrome_driver.execute_script(
        """
        shadowRoot = document.querySelector('#scorecardContainer').shadowRoot
        return shadowRoot.querySelectorAll("input[name=chamber]")
        """
    )

    for i in range(0, len(inputs)):
        chrome_driver.execute_script("arguments[0].click()", inputs[i])

        time.sleep(2)

        shadowRoot = chrome_driver.execute_script(
            """
        return document.querySelector('#scorecardContainer').shadowRoot
        """
        )
        time.sleep(5)
        
        page_source = shadowRoot.find_element(By.ID, "cards").get_attribute("innerHTML")

        extracted += extract(page_source)

        save_html(
            page_source,
            export_path / "HTML_FILES",
            filename,
        )

        time.sleep(2)

    records_extracted = dict(enumerate(extracted))
    return records_extracted
