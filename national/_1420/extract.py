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
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.common.exceptions import NoSuchElementException

from tqdm import tqdm

URL = "https://anca.org/congressional-report-cards/"


def extract(page_source, **additional_info):

    soup = BeautifulSoup(page_source, "html.parser")

    grades = soup.select("div.grade-current-year")

    extracted = []
    for grade in grades:

        candidate_container = grade.parent.parent
        candidate_info = candidate_container.select("div.col-md-3")[1]

        name = candidate_info.select_one("h2")
        other_info = candidate_info.select_one("h4")
        grade_desc = grade.parent.select_one("h2")

        extracted.append(
            {
                "name": name.get_text(strip=True, separator=", "),
                "info": other_info.get_text(strip=True) if other_info else None,
                (
                    "grades"
                    if not grade_desc
                    else grade_desc.get_text(strip=True, separator=" ")
                ): (grade.get_text(strip=True) if grade else None),
            }
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

    save_html(
        chrome_driver.page_source,
        export_path / "HTML_FILES",
        filename,
    )

    select_state = Select(chrome_driver.find_element(By.CSS_SELECTOR, "select#cat"))
    state_names = [o.get_attribute("value") for o in select_state.options[1:]]

    extracted = []

    p_bar = tqdm(total=len(state_names), desc="Begin extraction...")

    for s in state_names:
        chrome_driver.get(urljoin(URL, f"?state={s}"))

        save_html(
            chrome_driver.page_source,
            export_path / "HTML_STATE_FILES",
            f"{filename}{s}",
        )

        p_bar.desc = f"Extracting {s.title()}..."
        p_bar.refresh()
        
        extracted += extract(chrome_driver.page_source)

        p_bar.update(1)

    records_extracted = dict(enumerate(extracted))

    return records_extracted
