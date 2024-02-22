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


def extract(page_source, **additional_info):

    soup = BeautifulSoup(page_source, "html.parser")
    election_groups = soup.find_all("div", {"class": "election-group"})

    extracted = []

    def _print_candidate(soup: BeautifulSoup):
        candidate_endorsed = soup.find("div", {"class": "candidate-endorsed"}).find(
            "img"
        )

        return {
            "candidate_name": soup.find("div", {"class": "candidate-name"}).text.strip(
                "*"
            ),
            "candidate_grade": soup.find("div", {"class": "candidate-grade"}).text,
            "candidate_endorsed": "True" if candidate_endorsed else False,
            "candidate_status": soup.find("div", {"class": "candidate-incumbent"}).text,
        }

    def _election_position(soup: BeautifulSoup):
        print_candidates = soup.find_all("div", {"class": "print-candidate"})

        for candidate in print_candidates:
            yield _print_candidate(candidate) | {
                "election_location": soup.find(
                    "div", {"class": "election-location"}
                ).text
            }

    def _election_group(soup: BeautifulSoup):
        election_positions = soup.find_all(
            "div", {"class": "election-position-container"}
        )

        for election_position in election_positions:
            for candidate in _election_position(election_position):
                yield candidate | {
                    "election_type": soup.parent.parent["id"],
                    "election_date": soup.find("div", {"class": "election-date"}).text,
                }

    for group in election_groups:
        for candidate in _election_group(group):
            extracted.append(
                candidate | {"collected": str(datetime.now())} | additional_info
            )

    return extracted


def save_html(
    page_source,
    filename: str,
    filepath: Path,
    *additional_info,
):
    
    filepath.mkdir(exist_ok=True)

    soup = BeautifulSoup(page_source, "html.parser")
    timestamp = datetime.strftime(datetime.now(), "%Y-%m-%d-%H%M%S-%f")
    
    with open(filepath / (f"{filename}_{'-'.join(map(str, additional_info))}"
                          f"{'-' if additional_info else ''}{timestamp}.html"), 
              "w") as f:
        f.write(str(soup))


def save_pdf(
    driver: webdriver.Chrome,
    old_filename: str,
    new_filename: str,
    filepath: Path,
    *additional_info,
):

    filepath.mkdir(exist_ok=True)

    first_button = driver.find_element(By.CLASS_NAME, "btn-print-modal")
    first_button.click()

    time.sleep(1)

    second_button = driver.find_element(By.ID, "btn-print-voter-card")
    second_button.click()

    timestamp = datetime.strftime(datetime.now(), "%Y-%m-%d-%H%M%S-%f")

    pdf_filename = f"{old_filename}{"".join(map(str, additional_info))}.pdf"
    
    new_pdf_filename = (f"{new_filename}_{'-'.join(map(str, additional_info))}"
                        f"{'-' if additional_info else ''}{timestamp}")

    time_waited = 0
    while not (filepath / pdf_filename).exists() and time_waited < 10:
        time.sleep(2)
        time_waited += 2

    (filepath / pdf_filename).replace(filepath / f"{new_pdf_filename}.pdf")


def get_active_states(page_source):

    soup = BeautifulSoup(page_source, "html.parser")
    us_map = soup.find("svg", {"class", "us-map"})
    active_states = us_map.select(".state.state_hasElection")

    return sorted(set([path["data-fullname"] for path in active_states]))


def main(url, **module_vars):
    
    assert module_vars.get('PDF_OLD_PREFIX') != None # Please provide prefix of the PDF old filename
    assert module_vars.get('FILENAME_PREFIX') != None # Please provide the name in which the extract file will be saved
    assert module_vars.get('EXPORT_DIR') != None # Please provide the export directory of this module

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
        "savefile.default_directory": str(module_vars.get('EXPORT_DIR') / "PDF_FILES"),
    }
    
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
    chrome_driver.get(url)

    time.sleep(3)

    extracted = []

    for state in tqdm(get_active_states(chrome_driver.page_source)):

        state_dash = "-".join(state.split(" "))
        chrome_driver.get(f"{url}/grades/{state_dash}")

        extracted += extract(chrome_driver.page_source, state=state.title())
        save_html(
            chrome_driver.page_source,
            module_vars.get('FILENAME_PREFIX').format(filename='Ratings'),
            module_vars.get('EXPORT_DIR') / "HTML_FILES",
            state.title(),
        )
        save_pdf(
            chrome_driver,
            module_vars.get('PDF_OLD_PREFIX'),
            module_vars.get('FILENAME_PREFIX').format(filename='Ratings'),
            module_vars.get('EXPORT_DIR') / "PDF_FILES",
            state.title(),
        )

    records_extracted = {k: v for k, v in enumerate(extracted)}

    return records_extracted


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(prog="NRA webscrape")
    parser.add_argument(
        "-d",
        "--export_dir",
        type=Path,
        required=True,
        help="File directory of where extracted files exports to",
    )

    args = parser.parse_args()
    
    filename_prefix = f"{datetime.strftime(datetime.now(), "%Y")}_NA_NRA_{'{filename}'}"
    records_extracted = main("https://www.nrapvf.org",
                             PDF_OLD_PREFIX = "NRA-PVF _ Grades _ ",
                             FILENAME_PREFIX = filename_prefix,
                             EXPORT_DIR = args.export_dir,
                             )

    timestamp = datetime.strftime(datetime.now(), "%Y-%m-%d-%H%M%S-%f")

    df_extracted = pandas.DataFrame.from_dict(records_extracted, orient="index")
    df_extracted.to_csv(
        args.export_dir / f"{filename_prefix.format(filename='Ratings-Extract')}_{timestamp}.csv",
        index=False)
