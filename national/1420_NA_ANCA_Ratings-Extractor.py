# This is the webscraping script for Armenian National Committee of America (ANCA), sig_id=1420

import pandas

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from tqdm import tqdm



URL = "https://anca.org/report-card"
FILENAME = "_NA_ANCA_Ratings"
TIMESTAMP = datetime.strftime(datetime.now(), '%Y-%m-%d')


def get_states(driver:webdriver.Chrome):
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    options_states = soup.find('select', {'id': 'cat'}).find_all('option')
    states = [o['value'] for o in options_states[1:]]
    return states


def extract(driver:webdriver.Chrome, file=None):

    if file:
        soup = BeautifulSoup(file, 'html.parser')
    
    else:
        soup = BeautifulSoup(driver.page_source, 'html.parser')

    grades = soup.find_all('div', {'class': 'grade-current-year'})
    extracted = []
    for grade in grades:
        candidate_container = grade.parent.parent
        candidate_info = candidate_container.find_all('div', {'class': 'col-md-3'})[1]
        name = " ".join(map(lambda x: x if isinstance(x, str) else '', candidate_info.h2.contents))
        pst_info = candidate_info.h4
        grade_desc = grade.parent.h2
        extracted.append({'name': name.strip(),
                          'info': pst_info.text.strip() if pst_info else None,
                          'grades' if not grade_desc else ' '.join(grade_desc.text.split()):
                                  grade.text.strip() if grade else None})
    return extracted


def download_page(driver:webdriver.Chrome):

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    state = driver.current_url.split('=')[-1]

    HTML_FILES.mkdir(exist_ok=True)

    with open(HTML_FILES / f"{FILENAME}_{state}-{TIMESTAMP}.html", 'w') as f:
        f.write(soup.prettify())


def main():

    chrome_service = Service('chromedriver')
    chrome_options = Options()
    chrome_options.add_argument('incognito')
    chrome_options.add_argument('headless')
    chrome_driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    chrome_driver.get(URL)

    extracted = []

    for state in tqdm(get_states(chrome_driver)):
        chrome_driver.get(f"{URL}/?state={state}")
        extracted += extract(chrome_driver)
        download_page(chrome_driver)

    EXTRACT_FILES.mkdir(exist_ok=True)

    df = pandas.DataFrame.from_records(extracted)
    df.to_csv(EXTRACT_FILES / f"{FILENAME}-Extract_{TIMESTAMP}.csv", index=False)


if __name__ == "__main__":
    import sys

    _, EXPORT_DIR, *FILES = sys.argv

    EXPORT_DIR = Path(EXPORT_DIR)
    HTML_FILES = EXPORT_DIR / "HTML_FILES"
    EXTRACT_FILES = EXPORT_DIR / "EXTRACT_FILES"

    main()