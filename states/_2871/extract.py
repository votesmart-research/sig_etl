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
from selenium.common.exceptions import NoSuchElementException


URL = "http://arkansasreport.com/legislative-report-card/"


def extract(page_source, **additional_info):

    soup = BeautifulSoup(page_source, "html.parser")
    headers_container = soup.select(".post > .list-lawmakers.head-1 .title")
    rows_container = soup.select("#the-lawmakers .list-lawmakers")

    headers = [div.contents[0] for div in headers_container]

    extracted = []
    get_text = lambda x: x.get_text(strip=True)

    for row in rows_container:
        columns = row.find_all("div")
        url = columns[1].a["href"]
        params = url.lstrip("?").split("&")
        sig_candidate_id = params[-1].rpartition("=")[-1]

        extracted.append(
            {"sig_candidate_id": sig_candidate_id}
            | dict(zip(headers, map(get_text, columns)))
            | additional_info
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


def main(filename: str, export_path: Path, year: int, html_path: Path = None):

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

    chrome_driver.get(urljoin(URL, f"?scoreyear={year}"))

    # close overlay
    ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

    WebDriverWait(chrome_driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".post"))
    )

    save_html(
        chrome_driver.page_source,
        export_path / "HTML_FILES",
        filename,
    )

    extracted = extract(chrome_driver.page_source)
    records_extracted = dict(enumerate(extracted))

    return records_extracted
