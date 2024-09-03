from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urljoin

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.common.exceptions import NoSuchElementException

from tqdm import tqdm


URL = "https://index.texastaxpayers.com/legislative-sessions/"


def extract(page_source, **additional_info):

    soup = BeautifulSoup(page_source, "html.parser")
    name = soup.select_one("h1.name")
    party = soup.select_one("div.party")
    district = soup.select_one(".rep-details .district")
    score = soup.select_one(".score .chart-score")

    return {
        "name": name.get_text(strip=True, separator=";") if name else None,
        "party": party.get_text(strip=True) if party else None,
        "district": district.get_text(strip=True, separator=";") if district else None,
        "score": score.get_text(strip=True) if score else None,
    } | additional_info


def calculate_string(page_source):
    soup = BeautifulSoup(page_source, "html.parser")
    good_votes = soup.select(".vote-icon .check")
    bad_votes = soup.select(".vote-icon .x")
    return len(good_votes) / (len(good_votes) + len(bad_votes)) * 100


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


def get_candidate_urls(page_source, main_url):
    soup = BeautifulSoup(page_source, "html.parser")
    rows = soup.select("table.legislator-table tbody tr")

    urls = []

    for row in rows:
        columns = row.select("td")
        a = columns[0].find("a")
        if a:
            urls.append(urljoin(main_url, a["href"]))

    return urls


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

    chamber_select = Select(
        chrome_driver.find_element(By.CSS_SELECTOR, "#chamber.chamber-select")
    )

    candidate_urls = []

    for i in range(0, len(chamber_select.options)):
        chamber_select.select_by_index(i)
        candidate_urls += get_candidate_urls(
            chrome_driver.page_source, chrome_driver.current_url
        )

    extracted = []

    for url in tqdm(candidate_urls):

        chrome_driver.get(url)
        e = extract(chrome_driver.page_source)

        save_html(
            chrome_driver.page_source,
            export_path / "HTML_FILES",
            filename,
            url.split("/")[-2],
        )

        session_select = Select(
            chrome_driver.find_element(
                By.CSS_SELECTOR, "#legislative_session.session-select"
            )
        )

        total_sessions = len(session_select.options)

        scores = []

        for i in range(total_sessions - 1):
            session_select = Select(
                chrome_driver.find_element(
                    By.CSS_SELECTOR, "#legislative_session.session-select"
                )
            )
            session_select.select_by_index(i)
            scores.append(calculate_string(chrome_driver.page_source))

            save_html(
                chrome_driver.page_source,
                export_path / "HTML_FILES",
                filename,
                url.split("/")[-2],
            )

        if len(scores) > 0:
            lifetime_score = (sum(scores) + float(e.get("score"))) / (len(scores) + 1)
        else:
            lifetime_score = e.get("score")

        extracted.append(e | {"lifetime_score": lifetime_score})

    records_extracted = dict(enumerate(extracted))

    return records_extracted
