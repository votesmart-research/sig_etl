from datetime import datetime
from pathlib import Path
import time
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

URL = "https://web.archive.org/web/20241008134526/https://jstreetpac.org/candidates/"
WEBARCHIVE = "https://web.archive.org/"


def extract_cards(page_source, **additional_info) -> list[dict[str, str]]:

    soup = BeautifulSoup(page_source, "html.parser")
    extracted = []

    cards = soup.select("div.candidate-filter__grid > div.fancy-profile")

    for card in cards:

        style = card.get("style")
        if style is None or "display: none" in style:
            continue

        name = card.select_one("h3.fancy-profile__title")
        url = name.find("a")
        location = card.select_one("p.fancy-profile__meta-info")

        extracted.append(
            {
                "name": name.get_text(strip=True) if name else None,
                "url": url.get("href") if url else None,
                "location": location.get_text(strip=True) if location else None,
            }
        )

    return extracted


def extract_candidate(page_source, **additional_info):

    soup = BeautifulSoup(page_source, "html.parser")
    infos = soup.select("ul.candidate-hero__icon-list > li")

    return {
        "info": infos[-1].get_text(strip=True) if len(infos) > 1 else None
    } | additional_info


def extract_files(files: list[Path]):

    extracted = []

    for file in files:

        with open(file, "r") as f:
            extracted += extract_cards(f.read())

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


def remove_signin(driver):

    popup = driver.execute_script(
        """return document.querySelector("div.popup-container")"""
    )

    # print("Popup", popup)

    if popup is not None:
        driver.execute_script(
            """arguments[0].remove();""",
            popup,
        )


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

    # # close overlay
    # ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

    remove_signin(chrome_driver)

    office_to_select = ("Presidency", "House", "Senate")
    filter_labels = chrome_driver.find_elements(
        By.CSS_SELECTOR, "label.custom-radio__label"
    )

    extracted_cards = []

    for label in filter_labels:
        if label.text.strip() in office_to_select:
            label.click()

            save_html(
                chrome_driver.page_source,
                export_path / "HTML_FILES",
                filename,
                label.text,
            )
            extracted_cards += extract_cards(
                chrome_driver.page_source, office=label.text
            )
            label.click()

        else:
            continue

    extracted = []

    for _e in tqdm(extracted_cards, "Extracting candidates..."):
        candidate_url = _e.get("url")

        if candidate_url is None:
            continue

        if WEBARCHIVE in URL:
            chrome_driver.get(urljoin(WEBARCHIVE, f"/web/{candidate_url}"))
        else:
            chrome_driver.get(candidate_url)

        save_html(
            chrome_driver.page_source,
            export_path / "HTML_CANDIDATE_FILES",
            filename,
        )

        remove_signin(chrome_driver)
        e = _e | extract_candidate(chrome_driver.page_source)
        extracted.append(e)

    records_extracted = dict(enumerate(extracted))

    return records_extracted
