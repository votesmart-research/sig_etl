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
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.common.exceptions import NoSuchElementException


URL = "https://reportcard.flchamber.com/"


def extract(page_source, **additional_info):

    soup = BeautifulSoup(page_source, "html.parser")
    table = soup.select_one("table")

    def extract_table(table):

        headers = [th.get_text(strip=True) for th in table.thead.find_all("th")[1:]]
        rows = [tr.find_all("td") for tr in table.tbody.find_all("tr")]

        for row in rows:
            sig_candidate_id = row[0].a["href"].rpartition("/")[-1]
            columns = [sig_candidate_id] + [c.get_text(strip=True) for c in row[1:]]

            yield dict(zip(["sig_candidate_id"] + headers, columns)) | additional_info

    extracted = list(extract_table(table))

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


def main(filename: str, export_path: Path, html_path: Path = None, year: str = None):

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

    WebDriverWait(chrome_driver, 10).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "select[id$=_year]"))
    )

    session_select = Select(
        chrome_driver.find_element(By.CSS_SELECTOR, "select[id$=_year]")
    )

    if year is not None:
        for o in session_select.options:
            if year in o.text:
                session_select.select_by_value(o.get_attribute("value"))
                break
    else:
        session_select.select_by_index(len(session_select.options) - 1)

    WebDriverWait(chrome_driver, 10).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "table[class=table]"))
    )

    save_html(
        chrome_driver.page_source,
        export_path / "HTML_FILES",
        filename,
    )

    extracted = extract(chrome_driver.page_source, year=session_select.first_selected_option.text)
    records_extracted = dict(enumerate(extracted))

    return records_extracted
