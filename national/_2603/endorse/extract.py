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
from selenium.common.exceptions import NoSuchElementException


URLS = (
    "https://314action.org/endorsed-candidates/state-legislative-municipal/",
    "https://314action.org/endorsed-candidates/us-house-210810/",
    "https://314action.org/endorsed-candidates/us-senate-august-210810/",
)


def extract(page_source, **additional_info):

    soup = BeautifulSoup(page_source, "html.parser")
    extracted = []

    cards = soup.select("a[id*=panel_]")

    for card in cards:
        info = card.select_one("h4")
        name = card.select_one("h2")
        extracted.append(
            {"name": name.get_text(strip=True), "info": info.get_text(strip=True)}
        )

    return extracted


def extract_miniext(page_source, **additional_info):
    soup = BeautifulSoup(page_source, "html.parser")
    extracted = []

    cards = soup.select("li[data-testid='selected-linked-record']")

    for card in cards:
        name = card.select_one("p.text-base")
        infos = card.select("div[data-testid=detail-field]")

        _e = {}

        for i in infos:
            label = i.select_one("dt")
            text = i.select_one("dd")

            label_value = label.get_text(strip=True) if label else None

            if label_value is not None:
                _e[label_value] = text.get_text(strip=True) if text else None

        extracted.append({"name": name.get_text(strip=True)} | _e)

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

    extracted = []

    for url in URLS:
        chrome_driver.get(url)

        time.sleep(2)

        # close overlay
        ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

        save_html(
            chrome_driver.page_source,
            export_path / "HTML_FILES",
            filename,
        )

        try:
            iframe = chrome_driver.find_element(
                By.CSS_SELECTOR, "iframe[id*=miniExtIframe]"
            )
        except NoSuchElementException:
            iframe = None

        if iframe is not None:
            chrome_driver.switch_to.frame(iframe)
            while True:
                try:
                    load_more = chrome_driver.find_element(
                        By.XPATH, "//button[text()='Load more']"
                    )
                    load_more.click()
                    time.sleep(2)

                except NoSuchElementException:
                    load_more = None

                if load_more is None:
                    break

            extracted += extract_miniext(chrome_driver.page_source)
        else:
            extracted += extract(chrome_driver.page_source)

    records_extracted = dict(enumerate(extracted))

    return records_extracted
