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
from selenium.webdriver.support.ui import Select


URL = "http://aif.com/voterecords/reports.aspx"


def extract(page_source, **additional_info):

    soup = BeautifulSoup(page_source, "html.parser")
    table = soup.select_one("table[class=dataTable]")

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


def main(
    filename: str,
    export_path: Path,
    html_path: Path = None,
    year=None,
):

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

    year_select = Select(
        chrome_driver.find_element(By.CSS_SELECTOR, "select[name$=Year]")
    )

    if year is None:
        year_select.select_by_index(0)
    else:
        year_select.select_by_value(str(year))

    reports = chrome_driver.find_elements(By.CSS_SELECTOR, "input[value$=Alphabetical]")
    extracted = []
    selected_year = year_select.first_selected_option.text

    for i in range(0, len(reports)):

        r = chrome_driver.find_elements(By.CSS_SELECTOR, "input[value$=Alphabetical]")
        selected_office = r[i].get_attribute("value")
        r[i].click()

        # Explicitly let AJAX to send request before moving to the other element
        time.sleep(1)

        # Make sure that table exist before extracting
        WebDriverWait(chrome_driver, 10).until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "table[class=dataTable]")
            )
        )

        extracted += extract(
            chrome_driver.page_source, year=selected_year, office=selected_office
        )

        save_html(
            chrome_driver.page_source,
            export_path / "HTML_FILES",
            filename,
        )

    records_extracted = dict(enumerate(extracted))

    return records_extracted
