# This is the webscraping script for Freedom First Society (FFS), sig_id=2866
import time
from datetime import datetime
from pathlib import Path
from collections import defaultdict

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup


URL = "https://www.freedomfirstsociety.org/scorecard/"
RATINGS_METHODOLOGY = {"fa-check": "+", "fa-times": "-", "fa-question": "*"}


def extract(page_source, **additional_info):

    soup = BeautifulSoup(page_source, "html.parser")

    table = soup.find("div", {"id": "scorecard-wrapper"}).table
    bill_names = [p.text.strip() for p in table.find_all("th")[-1].find_all("p")]
    headers = ["state_id", "name"] + bill_names
    rows = table.tbody.find_all("tr")

    extracted = []

    for row in rows:
        columns = row.find_all("td")

        state_id_name = [td.text.strip() for td in columns[:2]]
        scores = [i["class"][-1] for i in columns[2:][-1].find_all("i")]

        translated_scores = [
            (
                RATINGS_METHODOLOGY.get(score)
                if score in RATINGS_METHODOLOGY.keys()
                else "?"
            )
            for score in scores
        ]

        extracted.append(
            dict(zip(headers, state_id_name + translated_scores)) | additional_info
        )

    return extracted


def extract_files(files: list[Path]):

    extracted_by_session = defaultdict(list)

    for file in files:
        cong_session = "-".join(file.name.split("_")[-1].split("-")[:2])

        with open(file, "r") as f:
            extracted_by_session[cong_session] += extract(f.read())

    return extracted_by_session


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
    filename: str,
    export_path: Path,
    cong_sessions: list,
    html_path: Path = None,
):

    if html_path:
        html_files = filter(
            lambda f: f.name.endswith(".html"),
            (export_path / html_path).iterdir(),
        )
        extracted_by_session = extract_files(
            sorted(html_files, key=lambda x: x.stat().st_ctime)
        )
        return extracted_by_session

    chrome_service = Service()
    chrome_options = Options()
    chrome_options.add_argument("incognito")
    chrome_options.add_argument("headless")
    chrome_driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    chrome_driver.get(URL)

    scorecard_form = WebDriverWait(chrome_driver, 10).until(
        EC.visibility_of_element_located(
            (By.CSS_SELECTOR, "div[ng-show='scorecard.main.visible']")
        )
    )
    # Backend framework doesn't load items even after the element is loaded
    time.sleep(3)

    select_congress = Select(
        scorecard_form.find_element(
            By.CSS_SELECTOR, "select[ng-model='scorecard.selected_congress']"
        )
    )
    select_session = Select(
        scorecard_form.find_element(
            By.CSS_SELECTOR, "select[ng-model='scorecard.selected_session']"
        )
    )
    select_office = Select(
        scorecard_form.find_element(
            By.CSS_SELECTOR, "select[ng-model='scorecard.selected_branch']"
        )
    )
    select_party = Select(
        scorecard_form.find_element(
            By.CSS_SELECTOR, "select[ng-model='scorecard.selected_party']"
        )
    )
    button_go = scorecard_form.find_element(
        By.CSS_SELECTOR, "button[ng-click='scorecard.load_bills()']"
    )

    extracted_by_session = defaultdict(list)

    for cong, session in cong_sessions:
        for option_o in select_office.options:
            for option_p in select_party.options:
                select_congress.select_by_visible_text(str(cong))
                select_session.select_by_visible_text(str(session))
                option_o.click()
                option_p.click()
                button_go.click()

                WebDriverWait(chrome_driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//div[@class='col-sm-2 ng-hide']")
                    )
                )

                save_html(
                    chrome_driver.page_source,
                    export_path / "HTML_FILES",
                    filename,
                    str(cong),
                    str(session),
                    option_o.text,
                    option_p.text,
                )

                congress_session = f"{cong}-{session}"
                extracted_by_session[congress_session] += extract(
                    chrome_driver.page_source, office=option_o.text, party=option_p.text
                )

    return extracted_by_session
