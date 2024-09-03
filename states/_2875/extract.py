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

from tqdm import tqdm

URL = "https://progressreport.betterutah.org/legislators/"


def extract(page_source, year, **additional_info):

    soup = BeautifulSoup(page_source, "html.parser")

    card_body = soup.select_one(".name-score-header .card-body")
    name = card_body.select_one(".card-title")
    info = card_body.select_one(".card-text")

    party = info.select_one("span svg")
    district = info.contents[-1] if info and info.contents else None

    rows = soup.select(f"#score-table-{year} tbody tr")

    sig_rating = ""

    for row in rows:
        good_scores = row.select(".text-green")
        bad_scores = row.select(".text-red")

        sig_rating += len(good_scores) * "+" + len(bad_scores) * "-"

        if len(good_scores) < 1 and len(bad_scores) < 1:
            sig_rating += "*"

    if sig_rating:
        our_rating = round(
            sig_rating.count("+") / (sig_rating.count("+") + sig_rating.count("-")) * 100
        )
    else:
        our_rating = None

    return {
        "name": name.get_text(strip=True) if name else None,
        "party": party["title"] if party else None,
        "district": district.lstrip(" | ") if district else None,
        "sig_rating": sig_rating,
        "our_rating": our_rating,
    }


def extract_files(files: list[Path], year):

    extracted = []

    for file in tqdm(files, desc="Reading files..."):
        with open(file, "r") as f:
            contents = f.read()
            extracted.append(extract(contents, year))

    records_extracted = dict(enumerate(extracted))

    return records_extracted


def get_candidate_urls(page_source):
    soup = BeautifulSoup(page_source, "html.parser")
    links = soup.select(".table tbody tr a")
    return [a["href"] for a in links]


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


def main(filename: str, export_path: Path, year: int, html_path: Path = None):

    if html_path:
        html_files = filter(
            lambda f: f.name.endswith(".html"),
            (export_path / html_path).iterdir(),
        )
        records_extracted = extract_files(
            sorted(html_files, key=lambda x: x.stat().st_ctime), year
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

    save_html(
        chrome_driver.page_source,
        export_path / "HTML_LIST_FILES",
        filename,
    )

    candidate_urls = get_candidate_urls(chrome_driver.page_source)
    extracted = []

    for url in tqdm(candidate_urls, desc="Extracting..."):
        chrome_driver.get(url)

        WebDriverWait(chrome_driver, 10).until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, ".name-score-header .card-body")
            )
        )

        save_html(
            chrome_driver.page_source,
            export_path / "HTML_FILES",
            filename,
            url.strip("/").rpartition("/")[-1],
        )
        extracted.append(extract(chrome_driver.page_source, year))

    records_extracted = dict(enumerate(extracted))

    return records_extracted
