import json
import time
from pathlib import Path
from datetime import datetime

# External packages and libraries
import pandas
from tqdm import tqdm
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options


URL = "https://www.nrapvf.org"
PDF_OLD_PREFIX = "NRA-PVF _ Grades _ "


def extract(page_source, **additional_info):

    soup = BeautifulSoup(page_source, "html.parser")
    election_groups = soup.find_all("div", {"class": "election-group"})

    extracted = []

    def _print_candidate(soup: BeautifulSoup):
        candidate_endorsed = soup.find("div", {"class": "candidate-endorsed"}).find(
            "img"
        )

        return {
            "candidate_name": soup.find("div", {"class": "candidate-name"})
            .get_text(strip=True)
            .strip("*"),
            "candidate_grade": soup.find("div", {"class": "candidate-grade"}).get_text(
                strip=True
            ),
            "candidate_endorsed": "True" if candidate_endorsed else False,
            "candidate_status": soup.find(
                "div", {"class": "candidate-incumbent"}
            ).get_text(strip=True),
        }

    def _election_position(soup: BeautifulSoup):
        print_candidates = soup.find_all("div", {"class": "print-candidate"})

        for candidate in print_candidates:
            yield _print_candidate(candidate) | {
                "election_location": soup.find(
                    "div", {"class": "election-location"}
                ).get_text(strip=True)
            }

    def _election_group(soup: BeautifulSoup):
        election_positions = soup.find_all(
            "div", {"class": "election-position-container"}
        )

        for election_position in election_positions:
            for candidate in _election_position(election_position):
                yield candidate | {
                    "election_type": soup.parent.parent["id"],
                    "election_date": soup.find(
                        "div", {"class": "election-date"}
                    ).get_text(strip=True),
                }

    for group in election_groups:
        for candidate in _election_group(group):
            extracted.append(
                candidate | {"collected": str(datetime.now())} | additional_info
            )

    return extracted


def extract_files(files: list):

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


def save_pdf(
    driver: webdriver.Chrome,
    filepath: Path,
    old_filename: str,
    new_filename: str,
    *additional_info,
):

    filepath.mkdir(exist_ok=True)

    first_button = driver.find_element(By.CLASS_NAME, "btn-print-modal")
    first_button.click()

    time.sleep(1)

    second_button = driver.find_element(By.ID, "btn-print-voter-card")
    second_button.click()

    timestamp = datetime.strftime(datetime.now(), "%Y-%m-%d-%H%M%S-%f")

    pdf_filename = f"{old_filename}{" ".join(map(str, additional_info))}.pdf"

    new_pdf_filename = (
        f"{new_filename}_{'-'.join(map(str, additional_info))}"
        f"{'-' if additional_info else ''}{timestamp}"
    )

    time_waited = 0

    while not (filepath / pdf_filename).exists() and time_waited <= 10:
        time.sleep(2)
        time_waited += 2

    if time_waited > 10 and not (filepath / pdf_filename).exists():
        print(f"TIMEOUT WARNING: '{pdf_filename}' is expected, but cannot be found.")

    (filepath / pdf_filename).replace(filepath / f"{new_pdf_filename}.pdf")


def get_active_states(page_source):

    soup = BeautifulSoup(page_source, "html.parser")
    us_map = soup.find("svg", {"class", "us-map"})
    active_states = us_map.select(".state.state_hasElection")

    return sorted(set([path["data-fullname"] for path in active_states]))


def main(filename, export_path: Path, html_path: Path = None):

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
    chrome_options.add_argument("kiosk-printing")

    print_settings = {
        "recentDestinations": [
            {
                "id": "Save as PDF",
                "origin": "local",
                "account": "",
            }
        ],
        "selectedDestinationId": "Save as PDF",
        "version": 2,
    }

    prefs = {
        "printing.print_preview_sticky_settings.appState": json.dumps(print_settings),
        "savefile.default_directory": str(export_path / "PDF_FILES"),
    }

    chrome_options.add_experimental_option("prefs", prefs)
    chrome_driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
    chrome_driver.get(URL)

    time.sleep(3)

    extracted = []

    for state in tqdm(get_active_states(chrome_driver.page_source)):

        state_dash = "-".join(state.split(" "))
        chrome_driver.get(f"{URL}/grades/{state_dash}")

        extracted += extract(chrome_driver.page_source, state=state.title())
        save_html(
            chrome_driver.page_source,
            export_path / "HTML_FILES",
            filename,
            state.title(),
        )
        save_pdf(
            chrome_driver,
            export_path / "PDF_FILES",
            PDF_OLD_PREFIX,
            filename,
            state.title(),
        )

    records_extracted = {k: v for k, v in enumerate(extracted)}

    return records_extracted
