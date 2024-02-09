
# Built-ins
import time
import json
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
PDF_PREFIX = "NRA-PVF _ Grades _ "
YEAR = datetime.strftime(datetime.now(), '%Y')
TIMESTAMP = datetime.strftime(datetime.now(), '%Y-%m-%d-%H%M')
FILENAME = f"{YEAR}_NA_NRA_Ratings{'{filetype}'}_{'{additional_info}'}{TIMESTAMP}.{'{ext}'}"


def extract(page_source, **additional_info):

    soup = BeautifulSoup(page_source, 'html.parser')
    election_groups = soup.find_all('div', {'class': 'election-group'})

    extracted = []

    def _print_candidate(soup: BeautifulSoup):
        candidate_endorsed = soup.find(
            'div', {'class': 'candidate-endorsed'}).find('img')

        return {'candidate_name': soup.find('div', {'class': 'candidate-name'}).text.strip('*'),
                'candidate_grade': soup.find('div', {'class': 'candidate-grade'}).text,
                'candidate_endorsed': 'True' if candidate_endorsed else False,
                'candidate_status': soup.find('div', {'class': 'candidate-incumbent'}).text}

    def _election_position(soup: BeautifulSoup):
        print_candidates = soup.find_all('div', {'class': 'print-candidate'})

        for candidate in print_candidates:
            yield _print_candidate(candidate) | \
                {'election_location': soup.find(
                    'div', {'class': 'election-location'}).text}

    def _election_group(soup: BeautifulSoup):
        election_positions = soup.find_all(
            'div', {'class': 'election-position-container'})

        for election_position in election_positions:
            for candidate in _election_position(election_position):
                yield candidate | {'election_type': soup.parent.parent['id'],
                                   'election_date': soup.find('div', {'class': 'election-date'}).text}

    for group in election_groups:
        for candidate in _election_group(group):
            extracted.append(candidate |
                             {'collected': str(datetime.now())} |
                             additional_info)

    return extracted


def save_html(page_source, file_directory: Path, **additional_info):

    file_directory.mkdir(exist_ok=True)

    soup = BeautifulSoup(page_source, 'html.parser')

    html_filename = FILENAME.format(filetype='-Extract',
                                    additional_info=f'{"-".join(additional_info.values())}-',
                                    ext='html')

    with open(file_directory / html_filename, 'w') as f:
        f.write(soup.prettify())


def save_extracted(records_extracted: dict[int, dict[str, str]], 
                   file_directory: Path, 
                   **additional_info):

    file_directory.mkdir(exist_ok=True)

    extract_filename = FILENAME.format(filetype='-Extract',
                                       additional_info=f'{"-".join(additional_info.values())}-',
                                       ext='csv')

    df = pandas.DataFrame.from_dict(records_extracted, orient='index')
    df.to_csv(file_directory / extract_filename, index=False)


def save_pdf(driver: webdriver.Chrome, 
             file_directory: Path, 
             timeout=10, 
             **additional_info):

    file_directory.mkdir(exist_ok=True)

    first_button = driver.find_element(By.CLASS_NAME, "btn-print-modal")
    first_button.click()

    time.sleep(1)

    second_button = driver.find_element(By.ID, "btn-print-voter-card")
    second_button.click()

    pdf_filename = f"{PDF_PREFIX}{additional_info.get('state')}.pdf"
    new_pdf_filename = FILENAME.format(filetype='',
                                       additional_info=f'{"-".join(additional_info.values())}-',
                                       ext='pdf')

    time_waited = 0
    while not (file_directory / pdf_filename).exists() and time_waited < timeout:
        time.sleep(2)
        time_waited += 2

    (file_directory / pdf_filename).replace(file_directory / new_pdf_filename)


def get_active_states(page_source):

    soup = BeautifulSoup(page_source, 'html.parser')
    us_map = soup.find('svg', {'class', 'us-map'})
    active_states = us_map.select('.state.state_hasElection')

    return sorted(set([path['data-fullname'] for path in active_states]))


def main(export_directory: Path):

    EXTRACT_FILES = export_directory / "EXTRACT_FILES"
    PDF_FILES = export_directory / "PDF_FILES"
    HTML_FILES = export_directory / "HTML_FILES"

    chrome_service = Service()
    chrome_options = Options()
    chrome_options.add_argument('incognito')
    chrome_options.add_argument('kiosk-printing')

    print_settings = {
            "recentDestinations": [{
                    "id": "Save as PDF",
                    "origin": "local",
                    "account": "",
                }],
                "selectedDestinationId": "Save as PDF",
                "version": 2
            }

    prefs = {
        'printing.print_preview_sticky_settings.appState': json.dumps(print_settings),
        'savefile.default_directory': str(PDF_FILES),
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    chrome_driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
    chrome_driver.get(URL)  

    time.sleep(3)

    extracted = []

    for state in tqdm(get_active_states(chrome_driver.page_source)):

        state_dash = "-".join(state.split(' '))
        chrome_driver.get(f"{URL}/grades/{state_dash}")

        extracted += extract(chrome_driver.page_source, state=state.title())
        save_html(chrome_driver.page_source, HTML_FILES, state=state.title())
        save_pdf(chrome_driver, PDF_FILES, state=state.title())

    records_extracted = {k: v for k, v in enumerate(extracted)}

    # Export files
    save_extracted(records_extracted, EXTRACT_FILES)

    return records_extracted


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(prog="NRA webscrape")
    parser.add_argument(
        "-d",
        "--exportdir",
        type=Path,
        required=True,
        help="File directory of where extracted files exports to",
    )
    
    args = parser.parse_args()

    main(args.url, args.exportdir)
