from datetime import datetime
from pathlib import Path
from collections import defaultdict
from urllib.parse import urljoin

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

URL = "https://ratings.yct.org/legislative-sessions/"


def extract(page_source, **additional_info):

    soup = BeautifulSoup(page_source, "html.parser")
    name = soup.find("h1", {"class": "name"})
    party = soup.find("div", {"class": "party"})
    district = soup.select_one(".rep-details .district")
    current_score = soup.select_one(".score .chart-score")
    career_score = soup.select_one(".historical-scores .career-rating span")

    return {
        "name": name.get_text(strip=True, separator="") if name else None,
        "party": party.get_text(strip=True) if party else None,
        "district": district.get_text(strip=True, separator="") if district else None,
        "sig_rating": current_score.get_text(strip=True) if current_score else None,
        "sig_lifetime": career_score.get_text(strip=True) if career_score else None,
    } | additional_info


def get_candidates_urls(page_source):
    soup = BeautifulSoup(page_source, "html.parser")
    legislators = soup.select(".legislator")
    return [l.find("a")["href"] for l in legislators if l.find("a")]


def extract_files(files: list[Path]):

    extracted = []

    for file in tqdm(files, desc="Extracting files..."):
        office = file.name.split("_")[-1].split("-")[0]
        with open(file, "r") as f:
            extracted.append(extract(f.read(), office=office))

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

    chrome_driver.get(URL)

    # close overlay
    ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

    select_session = Select(chrome_driver.find_element(By.ID, "legislative_session"))
    select_chamber = Select(chrome_driver.find_element(By.ID, "chamber"))

    select_session.select_by_index(0)

    candidate_urls = defaultdict(list)
    extracted = []

    for i in range(0, len(select_chamber.options)):
        select_chamber.select_by_index(i)
        selected_text = select_chamber.first_selected_option.text
        candidate_urls[selected_text] += get_candidates_urls(chrome_driver.page_source)

    progress_bar = tqdm(
        total=sum(len(u) for u in candidate_urls.values()),
        desc="Iterating Candidates...",
    )

    for office, urls in candidate_urls.items():
        for url in urls:
            chrome_driver.get(urljoin(URL, url))
            extracted.append(extract(chrome_driver.page_source, office=office))
            candidate_name = chrome_driver.current_url.strip("/").split("/")[-2]
            save_html(
                chrome_driver.page_source,
                export_path / "HTML_FILES",
                filename,
                office,
                candidate_name,
            )
            progress_bar.update(1)

    records_extracted = dict(enumerate(extracted))

    return records_extracted
