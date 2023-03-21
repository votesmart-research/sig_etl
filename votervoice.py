# This is a webscraping script for groups who uses Voter Voice.

import sys
import pandas

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime
from collections import defaultdict


TIMESTAMP = datetime.strftime(datetime.now(), '%Y-%m-%d')

RATINGS_METHODOLOGY = {'Voted with us': '+',
                       'Voted against us': '-',
                       'No position': '*',
                        None: ''}


def extract(driver:webdriver.Chrome, file:str=None):

    if file:
        soup = BeautifulSoup(file, 'html.parser')
    else:
        soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    office = soup.find('div', {'class':'vv-tab-menu-item-active'}).text.strip()
    sessions = soup.find_all('section', {'class':'vv-scorecard-section'})

    def _extract(row):
        columns = row.find_all('td')
        rating_string = [td.span['title'] if td.span else None for td in columns[2:]]
        translated_rating_string = "".join([RATINGS_METHODOLOGY[c] for c in rating_string])

        return {'info': columns[0]['title'],
                'rating': columns[1].text,
                'rating_string': translated_rating_string,
                'office': office}

    for session in sessions:
        span = session.header.text.strip()
        rows = session.table.tbody.find_all('tr')
        yield span, [_extract(row) for row in rows]


def download_page(driver:webdriver.Chrome):

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    HTML_FILES.mkdir(exist_ok=True)

    office = soup.find('div', {'class':'vv-tab-menu-item-active'}).text.strip()
    timestamp = datetime.now().strftime('%Y-%m-%d')

    with open(HTML_FILES / f"{FILENAME}_{office}-{timestamp}.html", 'w') as f:
        f.write(soup.prettify())


def extract_from_file(files:list):

    extracted  = defaultdict(list)

    for file in files:

        with open(file, 'r') as f:
            file_contents = f.read()

        for session, records in extract(driver=None, file=file_contents):
            extracted[session] += records
    
    EXTRACT_FILES.mkdir(exist_ok=True)

    for session, records in extracted.items():
        if records:
            df = pandas.DataFrame.from_records(records)
            df.to_csv(EXTRACT_FILES / f"{session}{FILENAME}-Extract.csv", index=False)


def main():
    
    chrome_service = Service('chromedriver')
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('incognito')
    chrome_options.add_argument('headless')
    chrome_driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    chrome_driver.get(URL)

    try:
        WebDriverWait(chrome_driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, '//table[@class="vvScorecardAggregate"]/tbody/tr'))
        )
    except TimeoutException:
        print("An error occurred: The page could not load.")
        chrome_driver.quit()
        exit()

    offices = chrome_driver.find_elements(By.XPATH, '//section[@id="vvConsolidatedScorecardResults"]//div[@class="vv-tab-menu-item-container"]')
    extracted = defaultdict(list)

    for office in offices:
        office.click()

        for session, records in extract(chrome_driver):
                extracted[session] += records

        download_page(chrome_driver)

    EXTRACT_FILES.mkdir(exist_ok=True)

    for session, records in extracted.items():
        if records:
            df = pandas.DataFrame.from_records(records)
            df.to_csv(EXTRACT_FILES / f"{session}{FILENAME}-Extract.csv", index=False)


if __name__ == '__main__':

    _, EXPORT_DIR, URL = sys.argv

    EXPORT_DIR = Path(EXPORT_DIR)
    HTML_FILES = EXPORT_DIR / "HTML_FILES"
    EXTRACT_FILES = EXPORT_DIR / "EXTRACT_FILES"
    
    GROUP_ABV = URL.split('/')[4]
    FILENAME = f"_{GROUP_ABV}_Ratings"

    main()
