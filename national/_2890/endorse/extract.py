import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlencode

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from tqdm import tqdm

URL = "https://www.newpolitics.org/our-candidates"
PARAMS = {
    "year": None,
    "level-of-government": "Federal,State",
}


def extract_cards(page_source, **additional_info):

    soup = BeautifulSoup(page_source, "html.parser")
    extracted = []

    cards = soup.select("div.candidates_list_item")
    for card in cards:
        candidate_url = card.select_one("a.candidates_item_link")
        name = card.select_one("h4")
        info = card.select_one("div.candidates_item_content_bottom > div.hide")

        state = info.select_one("div[fs-cmsfilter-field=state]") if info else None
        year = info.select_one("div[fs-cmsfilter-field=year]") if info else None
        level = (
            info.select_one("div[fs-cmsfilter-field=level-of-government]")
            if info
            else None
        )

        extracted.append(
            {
                "name": name.get_text(strip=True) if name else None,
                "state": state.get_text(strip=True) if state else None,
                "year": year.get_text(strip=True) if year else None,
                "level": level.get_text(strip=True) if level else None,
                "url": candidate_url.get("href"),
            }
        )

    return extracted


def extract_candidate(page_source, card_info: dict):
    soup = BeautifulSoup(page_source, "html.parser")

    position = soup.select_one("div.candidate_item_role")

    return card_info | {"position": position.get_text(strip=True) if position else None}


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


def main(filename: str, export_path: Path, html_path: Path = None, year: str = None):

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

    if year is not None:
        PARAMS["year"] = year

    query_string = f"?{urlencode(PARAMS)}"

    chrome_driver.get(urljoin(URL, query_string))

    time.sleep(5)

    # close overlay
    ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

    while True:
        try:

            view_more = WebDriverWait(chrome_driver, 3).until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, "a.w-pagination-next")
                )
            )
        except TimeoutException or NoSuchElementException:
            view_more = None

        if view_more is None:
            break
        else:
            chrome_driver.execute_script("arguments[0].click()", view_more)

    time.sleep(3)

    save_html(
        chrome_driver.page_source,
        export_path / "HTML_FILES",
        filename,
    )

    extracted_cards = extract_cards(chrome_driver.page_source)
    extracted = []

    for card_info in tqdm(extracted_cards, desc="Extracting candidates..."):
        url = card_info.get("url")

        if url is None:
            continue
        else:
            chrome_driver.get(urljoin(URL, url))

        save_html(
            chrome_driver.page_source,
            export_path / "HTML_CANDIDATE_FILES",
            filename,
        )

        extracted.append(extract_candidate(chrome_driver.page_source, card_info))

    records_extracted = dict(enumerate(extracted))

    return records_extracted
