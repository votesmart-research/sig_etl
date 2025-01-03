# This is a webscraping script for groups who uses Voter Voice.

from pathlib import Path
from datetime import datetime
from collections import defaultdict


import pandas
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from tqdm import tqdm


RATINGS_METHODOLOGY = {
    "Voted with us": "+",
    "Voted against us": "-",
    "No position": "*",
    "vvSupportContainer": "+",
    "vvOpposeContainer": "-",
    "vvNeutralContainer": "*",
}


def extract(page_source):
    soup = BeautifulSoup(page_source, "html.parser")

    office = soup.find("div", {"class": "vv-tab-menu-item-active"}).get_text(strip=True)
    sessions = soup.find_all("section", {"class": "vv-scorecard-section"})

    def translate_ratings(rating_columns):
        rating_string = ""
        for td in rating_columns:
            title = td.span.get("title") if td.span else None
            class_ = td.span.get("class") if td.span else None

            if title is None or title not in RATINGS_METHODOLOGY:
                for m in RATINGS_METHODOLOGY:
                    if class_ and m in class_:
                        rating_string += RATINGS_METHODOLOGY.get(m)
                        break
            elif title in RATINGS_METHODOLOGY:
                rating_string += RATINGS_METHODOLOGY.get(title)
        return rating_string

    def _extract_row(row):
        columns = row.find_all("td")
        # rating_string = [td.span["title"] if td.span else None for td in columns[2:]]
        # translated_rating_string = "".join(
        #     [RATINGS_METHODOLOGY.get(c) for c in rating_string if RATINGS_METHODOLOGY.get(c)]
        # )
        translated_rating_string = translate_ratings(columns[2:])
        return {
            "info": columns[0]["title"],
            "sig_rating": columns[1].get_text(strip=True),
            "sig_rating_string": translated_rating_string,
            "office": office,
        }

    for session in sessions:
        span = session.header.get_text(strip=True)
        rows = session.table.tbody.find_all("tr")
        yield span, [_extract_row(row) for row in rows]


def extract_files(files: list):
    extract_by_session = defaultdict(list)

    for file in files:
        with open(file, "r") as f:
            page_source = f.read()
            for session, records in extract(page_source):
                extract_by_session[session] += records

    return extract_by_session


def save_html(page_source, filepath, *additional_info):
    soup = BeautifulSoup(page_source, "html.parser")

    filepath = Path(filepath) / "HTML_FILES"
    filepath.mkdir(exist_ok=True)

    timestamp = datetime.strftime(datetime.now(), "%Y-%m-%d-%H%M%S-%f")

    with open(
        filepath / f"Ratings_{'-'.join(map(str, additional_info))}"
        f"{'-' if additional_info else ''}{timestamp}.html",
        "w",
    ) as f:
        f.write(str(soup))


def save_extract(extracted: list[dict], filepath, *additional_info):
    filepath = Path(filepath) / "EXTRACT_FILES"
    filepath.mkdir(exist_ok=True)

    timestamp = datetime.strftime(datetime.now(), "%Y-%m-%d-%H%M%S-%f")

    df = pandas.DataFrame.from_records(extracted)
    df.to_csv(
        filepath / f"Ratings-Extract_{'-'.join(map(str, additional_info))}"
        f"{'-' if additional_info else ''}{timestamp}.csv",
        index=False,
    )


def main(url, export_path: Path):
    chrome_service = Service()
    chrome_options = Options()
    chrome_options.add_argument("incognito")
    # chrome_options.add_argument("headless")
    chrome_driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    chrome_driver.get(url)

    try:
        WebDriverWait(chrome_driver, 30).until(
            EC.visibility_of_all_elements_located(
                (By.CSS_SELECTOR, "table.vvScorecardAggregate tbody tr")
            )
        )
    except TimeoutException:
        chrome_driver.quit()
        print("Taking too long to load...")
        return []

    offices = chrome_driver.find_elements(
        By.XPATH,
        "section#vvConsolidatedScorecardResults div.vv-tab-menu-item-container]",
    )

    extract_by_session = defaultdict(list)
    p_bar = tqdm(total=len(offices))

    for office in offices:
        p_bar.desc = f"Extracting {office.text}"
        office.click()
        for session, records in extract(chrome_driver.page_source):
            extract_by_session[session] += records

        save_html(chrome_driver.page_source, export_path, office.text)
        p_bar.update(1)

    return extract_by_session
