import re
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


def extract(page_source, year_to_get, **additional_info):

    soup = BeautifulSoup(page_source, "html.parser")
    score_table = soup.find("table")

    info = soup.select_one(".romana_allPage_text h1")

    rows = score_table.select("tr")

    scores = {}

    for row in rows:
        cells = row.select('td[align="center"]')
        i = 0
        while i < len(cells):
            # Skip cells with rowspan attribute
            if cells[i].has_attr("rowspan"):
                i += 1
                continue

            year = cells[i].get_text(strip=True)
            colspan = int(cells[i + 1].get("colspan", 1))

            score = cells[i + 1].get_text(strip=True)
            scores[year] = score
            i += 2 + (2 - colspan)

    latest = max(year for year in scores if year and year.isdigit())
    cumulative = next(filter(lambda x: "cumulative" in x.lower(), scores), None)

    if "Borders" in info.get_text(strip=True) or "Shackleford" in info.get_text(
        strip=True
    ):
        print(scores)

    return {
        "info": info.get_text(strip=True) if info else None,
        "sig_rating": (scores.get(year_to_get) if year_to_get else scores.get(latest)),
        "sig_lifetime": scores.get(cumulative),
    } | additional_info


def get_candidate_pages(page_source):

    soup = BeautifulSoup(page_source, "html.parser")
    tables = soup.select("table")

    def get_pages(table):
        rows = table.select("tbody tr")[1:]
        for row in rows:
            columns = row.select("td")
            anchor = columns[1].a if len(columns) > 1 and columns[1].find("a") else None
            link = anchor["href"] if "href" in anchor.attrs else None
            if link is not None:
                yield link

    return list(get_pages(tables[1])) + list(get_pages(tables[-1]))


def extract_files(files: list[Path], year):

    extracted = []

    for file in tqdm(files, desc="Extracting Files..."):

        with open(file, "r", encoding="utf-8") as f:
            extracted.append(extract(f.read(), year))

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
        encoding="utf-8",
    ) as f:
        f.write(str(soup))


def main(
    filename: str,
    export_path: Path,
    url,
    year=None,
    html_path: Path = None,
):

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

    chrome_driver.get(url)

    # close overlay
    ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

    save_html(
        chrome_driver.page_source,
        export_path / "HTML_LIST_FILES",
        filename,
        "main_page",
    )

    extracted = []
    candidate_pages = get_candidate_pages(chrome_driver.page_source)

    for c_url in tqdm(candidate_pages, desc="Iterating Pages..."):

        chrome_driver.get(c_url)
        extracted.append(extract(chrome_driver.page_source, year_to_get=year))

        p_link = c_url.rpartition("/")[-1]

        save_html(
            chrome_driver.page_source,
            export_path / "HTML_FILES",
            filename,
            p_link,
        )

    records_extracted = dict(enumerate(extracted))

    return records_extracted
