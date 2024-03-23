import re
from collections.abc import Generator

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
)

from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from tqdm import tqdm
from urllib.parse import urljoin


def extract_candidate(page_source, **additional_info):
    soup = BeautifulSoup(page_source, "html.parser")

    container = soup.find("div", {"class": "bt50-scorecard-container"})
    info = container.find("div", {"class": "legislator-sub-head"})

    score_containers = container.find_all("p", {"class": "legislator-detail-score"})
    score_headers = [p.strong.text.strip() for p in score_containers]
    scores = [p.span.text.strip() for p in score_containers]

    return (
        {
            "sig_candidate_id": container["data-legislatorid"],
            "info": info.text.strip() if info else None,
        }
        | dict(zip(score_headers, scores))
        | additional_info
    )


def extract_cards(page_source, **additional_info) -> Generator[str, tuple[str, dict]]:
    soup = BeautifulSoup(page_source, "html.parser")
    container = soup.find("div", {"id": "legislators-container"})

    for card in container.find_all("div", {"class": "card"}):
        url = card.find("a")["href"]
        id_segment_match = re.search(r"/+([^\W_]\w*)\W*$", url)
        sig_candidate_id = id_segment_match.group(1) if id_segment_match else ""
        party = card.find("div", {"class": "party"})
        name = card.find("div", {"class": "name"})

        yield url, {
            "sig_candidate_id": sig_candidate_id,
            "name": name.text.strip() if name else None,
            "party": party.find("div", {"class": "value"}).text if party else None,
        } | additional_info


def extract_files(files: list):

    with open(files[0], "r") as f:
        card_records = {
            record["sig_candidate_id"]: record for _, record in extract_cards(f)
        }

    records_extracted = []

    for file in tqdm(files[1:]):
        with open(file, "r") as f:
            page_source = f.read()
            candidate_extract = extract_candidate(page_source)
            card_record = card_records.get(candidate_extract["sig_candidate_id"])
            records_extracted.append(card_record | candidate_extract)

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


def main(url, filename: str, export_path: Path, html_path:Path = None):

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

    chrome_driver.get(url)

    # close overlay
    ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

    try:
        WebDriverWait(chrome_driver, 10).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//div[@id='legislators-container']//div[@class='pure-g legislator-list']",
                )
            )
        )
    except TimeoutException:
        print("Cannot find Legislator Container. Quitting...")
        chrome_driver.quit()
        exit()

    while True:
        try:
            pagination = chrome_driver.find_element(
                By.XPATH, "//div[@class='pagination pure-u-md-1 pure-u-lg-3-4']"
            )
            pagination.click()

        except NoSuchElementException:
            break
        except ElementClickInterceptedException:
            pass

    extracted = []

    card_records = list(extract_cards(chrome_driver.page_source))
    save_html(
        chrome_driver.page_source,
        export_path / "HTML_FILES",
        filename,
    )

    for candidate_url, card_record in tqdm(card_records):
        chrome_driver.get(urljoin(chrome_driver.current_url, candidate_url))
        _extracted = extract_candidate(chrome_driver.page_source)

        chrome_driver.execute_script("window.history.go(-1)")

        save_html(
            chrome_driver.page_source,
            export_path / "HTML_FILES",
            filename,
            _extracted["sig_candidate_id"],
        )

        extracted.append(_extracted | card_record)

    records_extracted = dict(enumerate(extracted))
    return records_extracted
