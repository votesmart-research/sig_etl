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
            # "sig_candidate_id": container["data-legislatorid"],
            "info": info.text.strip() if info else None,
        }
        | dict(zip(score_headers, scores))
        | additional_info
    )


def get_vote_index(page_source):
    soup = BeautifulSoup(page_source, "html.parser")
    table = soup.select_one(".bill-table .pure-table")

    if not table:
        return {}

    headers = [th.text for th in table.thead.find_all("th")]
    rows = [tr.find_all("td") for tr in table.tbody.find_all("tr")]

    extracted_table = [
        dict(zip(headers, map(lambda x: x.get_text(strip=True), row))) for row in rows
    ]

    possible_score = 0

    for r in extracted_table:
        possible_score += abs(float(r.get("Score"))) if r.get("Score") else 0

    container = soup.find("div", {"class": "bt50-scorecard-container"})
    score_containers = container.find_all("p", {"class": "legislator-detail-score"})
    score_headers = [p.strong.text.strip() for p in score_containers]
    scores = [p.span.text.strip() for p in score_containers]

    vote_indices = {}

    def calculate_vote_index(total_score, possible_score):
        return ((total_score + possible_score) / (2 * possible_score)) * 100

    for score_header, score in zip(score_headers, scores):

        vote_indices["possible_score"] = possible_score
        vote_indices[f"vote_index_{score_header}"] = calculate_vote_index(
            float(score), possible_score
        )

    return vote_indices


def extract_cards(page_source, **additional_info) -> Generator[str, tuple[str, dict]]:

    soup = BeautifulSoup(page_source, "html.parser")
    container = soup.find("div", {"id": "legislators-container"})

    for card in container.find_all("div", {"class": "card"}):
        url = card.find("a")["href"]
        id_segment_match = re.search(r"/+([^\W_]\w*)\W*$", url)
        sig_candidate_id = id_segment_match.group(1) if id_segment_match else ""
        party = card.select_one(".party .value")
        name = card.find("div", {"class": "name"})
        info = card.find("div", {"class": "info"})

        yield url, {
            "sig_candidate_id": sig_candidate_id,
            "name": name.get_text(strip=True, separator=", ") if name else None,
            "party": party.get_text(strip=True, separator=", ") if party else None,
            "card_info": info.get_text(strip=True, separator=", ") if info else None,
        } | additional_info


def extract_files(files: list[Path], candidate_files: list[Path], vote_index=False):

    card_records = {}

    for file in files:
        with open(file, "r") as f:
            card_records.update(
                {record["sig_candidate_id"]: record for _, record in extract_cards(f)}
            )

    extracted = []

    for c_file in tqdm(candidate_files[1:]):
        sig_candidate_id = "".join(c_file.name.split("_")[-1].split("-")[:-5])

        with open(c_file, "r") as f:
            page_source = f.read()
            card_record = card_records.get(sig_candidate_id)
            candidate_extract = extract_candidate(page_source)

            if vote_index:
                vi = get_vote_index(page_source)
                extracted.append(card_record | candidate_extract | vi)
            else:
                extracted.append(card_record | candidate_extract)

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
    url,
    filename: str,
    export_path: Path,
    html_path: Path = None,
    candidates_html_path: Path = None,
    vote_index: bool = False,
):

    if html_path:
        html_files = filter(
            lambda f: f.name.endswith(".html"),
            (export_path / html_path).iterdir(),
        )
        candidates_html_files = filter(
            lambda f: f.name.endswith(".html"),
            (export_path / candidates_html_path).iterdir(),
        )
        records_extracted = extract_files(
            sorted(html_files, key=lambda x: x.stat().st_ctime),
            sorted(candidates_html_files, key=lambda x: x.stat().st_ctime),
            vote_index,
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
                    By.CSS_SELECTOR,
                    "div#legislators-container div.legislator-list",
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
                By.CSS_SELECTOR, "div#scorecard-app div.pagination"
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

        if vote_index:
            try:
                WebDriverWait(chrome_driver, 10).until(
                    EC.visibility_of_element_located(
                        (
                            By.CSS_SELECTOR,
                            ".bill-table tbody",
                        )
                    )
                )
            except TimeoutException:
                pass

        save_html(
            chrome_driver.page_source,
            export_path / "HTML_FILES_CANDIDATE",
            filename,
            card_record["sig_candidate_id"],
        )

        _extracted = extract_candidate(chrome_driver.page_source)

        if vote_index:
            vi = get_vote_index(chrome_driver.page_source)
            extracted.append(_extracted | card_record | vi)
        else:
            extracted.append(_extracted | card_record)

        chrome_driver.execute_script("window.history.go(-1)")

    records_extracted = dict(enumerate(extracted))
    return records_extracted
