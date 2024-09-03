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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException

from tqdm import tqdm


URL = "https://climatehawksvote.com/scorecard/alabama"


def extract(page_source, **additional_info):

    soup = BeautifulSoup(page_source, "html.parser")

    sheet_container = soup.find("div", {"id": "sheets-viewport"})
    table = sheet_container.find("table")

    def extract_table(table):

        headers = [td.get_text(strip=True) for td in table.tbody.tr.find_all("td")]
        rows = [tr.find_all("td") for tr in table.tbody.find_all("tr")[1:]]

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
            state_name = file.name.split("_")[-1].split("-")[0]
            extracted += extract(f.read(), state_name=state_name)

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


def get_states(page_source):
    soup = BeautifulSoup(page_source, "html.parser")
    select = soup.find("div", {"state-dropdown"}).find("select")
    return [o.get("value") for o in select.find_all("option") if o.get("value")]


def main(filename: str, export_path: Path, html_path: Path = None):

    # if html_path:
    #     html_files = filter(
    #         lambda f: f.name.endswith(".html"),
    #         (export_path / html_path).iterdir(),
    #     )
    #     records_extracted = extract_files(
    #         sorted(html_files, key=lambda x: x.stat().st_ctime)
    #     )
    #     return records_extracted

    chrome_service = Service()
    chrome_options = Options()
    chrome_options.add_argument("incognito")
    chrome_options.add_argument("headless")
    chrome_driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    chrome_driver.get(URL)

    # close overlay
    ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

    extracted = []

    for state_url in tqdm(get_states(chrome_driver.page_source), desc="Scraping"):

        _state_name = state_url.strip("/").rpartition("/")[-1]
        state_name = " ".join(_state_name.split("-")).title()

        chrome_driver.get(state_url)
        iframe = chrome_driver.execute_script(
            """
            return document.querySelector("iframe[src*='docs.google.com']")
            """
        )

        chrome_driver.switch_to.frame(iframe)

        sheets_select = chrome_driver.execute_script(
            """
            return document.querySelectorAll(".switcherTable td")
            """)

        for i in range(0, len(sheets_select)):

            sheets_select[i].click()

            time.sleep(2)

            iframe_2 = chrome_driver.execute_script(
            """
            return document.querySelector("#pageswitcher-content")    
            """
            )
            chrome_driver.switch_to.frame(iframe_2)


            extracted += extract(chrome_driver.page_source, state_name=state_name)

            save_html(
                chrome_driver.page_source, export_path / "HTML_FILES", filename, state_name
            )

            chrome_driver.switch_to.default_content()


            iframe = chrome_driver.execute_script(
                """
                return document.querySelector("iframe[src*='docs.google.com']")
                """
            )

            chrome_driver.switch_to.frame(iframe)

            sheets_select = chrome_driver.execute_script(
                """
                return document.querySelectorAll(".switcherTable td")
                """
            )


    records_extracted = dict(enumerate(extracted))
    return records_extracted
