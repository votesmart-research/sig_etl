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
    None: "",
}


def extract(page_source):
    soup = BeautifulSoup(page_source, "html.parser")

    office = soup.find("div", {"class": "vv-tab-menu-item-active"}).get_text(strip=True)
    sessions = soup.find_all("section", {"class": "vv-scorecard-section"})

    def _extract_row(row):
        columns = row.find_all("td")
        rating_string = [td.span["title"] if td.span else None for td in columns[2:]]
        translated_rating_string = "".join(
            [RATINGS_METHODOLOGY.get(c) for c in rating_string]
        )

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
    for file in files:
        with open(file, "r") as f:
            file_contents = f.read()

        for session, records in extract(driver=None, file=file_contents):
            save_extract(records, session)


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
        WebDriverWait(chrome_driver, 10).until(
            EC.visibility_of_all_elements_located(
                (By.XPATH, '//table[@class="vvScorecardAggregate"]/tbody/tr')
            )
        ) 
    except TimeoutException:
        chrome_driver.quit()
        return "Taking too long to load..."

    offices = chrome_driver.find_elements(
        By.XPATH,
        '//section[@id="vvConsolidatedScorecardResults"]//div[@class="vv-tab-menu-item-container"]',
    )

    extracted_by_session = defaultdict(list)
    p_bar = tqdm(total=len(offices))

    for office in offices:
        p_bar.desc = f"Extracting {office.text}"
        office.click()
        for session, records in extract(chrome_driver.page_source):
            extracted_by_session[session] += records
            save_extract(records, export_path, office.text, session)

        save_html(chrome_driver.page_source, export_path, office.text)
        p_bar.update(1)
        
    return extracted_by_session


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(prog="Votervoice Webscrape")
    parser.add_argument(
        "-u",
        "--url",
        type=str,
        required=True,
        help="website url where the ratings are located",
    )
    parser.add_argument(
        "-d",
        "--exportdir",
        type=Path,
        required=True,
        help="file directory of where the files exports to",
    )
    parser.add_argument(
        "-f", "--htmldir", type=Path, help="file directory of html files to read"
    )

    args = parser.parse_args()

    if args.htmldir:
        html_files = filter(
            lambda f: f.name.endswith(".html"),
            (args.exportdir / args.htmldir).iterdir(),
        )
        extract_files(sorted(html_files, key=lambda x: x.stat().st_ctime))
    else:
        main(args.url, args.exportdir)
