import re
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
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from tqdm import tqdm


URL = "https://thecannabisindustry.org/ncia-news-resources/congressional-scorecards/"


def extract(page_source, **additional_info):

    soup = BeautifulSoup(page_source, "html.parser")

    extracted = []
    cards = soup.select("section.scorecards div.rep")

    for rep_card in cards:

        info = rep_card.select_one("div.info")
        party = info.select_one("h5.party")
        name = info.select_one("h3")
        scores = rep_card.select("div.score h3")

        if party.span:
            district = party.span.get_text(strip=True)
            party.span.decompose()

        else:
            district = None

        extracted.append(
            {
                "name": name.get_text(strip=True) if name else None,
                "party": party.get_text(strip=True) if party else None,
                "district": district,
                "sig_rating": "/".join([s.get_text(strip=True) for s in scores]),
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

    try:
        WebDriverWait(chrome_driver, 15).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "#mapdivc svg"))
        )

    except TimeoutException:
        print("ERROR. Page did not load.")
        chrome_driver.quit()
        exit()

    paths = chrome_driver.find_elements(By.CSS_SELECTOR, "#mapdivc path")

    save_html(
        chrome_driver.page_source,
        export_path / "HTML_FILES",
        filename,
    )

    state_names = []

    for path in paths:
        if path and path.get_attribute("role") == "menuitem":
            pass
        else:
            continue

        state_name = re.match(
            r"^[A-Z][a-z]+(?: [A-Z][a-z]+)?", path.get_attribute("aria-label")
        )
        state_names.append(state_name.group().lower())

    extracted = []

    for state in tqdm(state_names):
        chrome_driver.get(urljoin(URL, state))
        extracted += extract(chrome_driver.page_source, state=state)
        save_html(
            chrome_driver.page_source,
            export_path / "HTML_STATE_FILES",
            filename,
            state,
        )

    records_extracted = dict(enumerate(extracted))

    return records_extracted
