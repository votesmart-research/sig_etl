from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait, Select


URL = "https://awionline.org/compassion-index#/legislators"


def extract(page_source):

    soup = BeautifulSoup(page_source, "html.parser")
    table = soup.find("table", {"class": "congressweb-module-listTable"})

    headers = [th.get_text(strip=True) for th in table.find_all("th")]
    rows = [tr.find_all("td") for tr in table.find_all("tr")[1:]]

    def get_text(x):
        return x.get_text(strip=True, separator=" ")

    return [dict(zip(headers, map(get_text, row))) for row in rows]


def extract_files(files: list):

    extracted = []

    for file in files:

        with open(file, "r") as f:
            extracted += extract(f.read())

    return extracted


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

    chrome_service = Service()
    chrome_options = Options()
    chrome_options.add_argument("incognito")
    chrome_options.add_argument("headless")
    chrome_driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    chrome_driver.get(URL)

    # close overlay
    ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

    to_select = ["118-Senate", "118-House"]

    extracted = []

    for session in to_select:

        chrome_driver.refresh()

        iframe = WebDriverWait(chrome_driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#iframe iframe"))
        )

        chrome_driver.switch_to.frame(iframe)

        select = Select(
            chrome_driver.find_element(By.CSS_SELECTOR, "select[name=congress_chamber]")
        )

        button = chrome_driver.find_element(
            By.CSS_SELECTOR,
            "form[action='/AWI/legislators/membercompassionindex'] input",
        )

        select.select_by_value(session)
        button.click()

        WebDriverWait(chrome_driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "table.congressweb-module-listTable")
            )
        )

        extracted += extract(chrome_driver.page_source)
        save_html(chrome_driver.page_source, export_path / "HTML_FILES", filename)

    records_extracted = dict(enumerate(extracted))
    return records_extracted
