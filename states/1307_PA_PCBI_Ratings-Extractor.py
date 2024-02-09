# This is the webscraping script for Pennsylvania Chamber of Business and Industry, sig_id = 1307

import sys
import pandas

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path


URL = "https://www.pachamber.org/advocacy/chamber_pac/legislative_scorecard/"
FILENAME = "_PA_PCBI_Ratings"
TIMESTAMP = datetime.strftime(datetime.now(), '%Y-%m-%d')


def extract(driver:webdriver.Chrome, file=None):

    def extract_table(table):
        headers = ['sig_candidate_id']+ [th.text.strip() for th in table.thead.find_all('td')]
        rows = [[tr['leg_vv_id']] + tr.find_all('td') for tr in table.tbody.find_all('tr')]

        get_text = lambda x: x.text.strip() if not isinstance(x, str) else x

        return [dict(zip(headers, map(get_text, row))) for row in rows]
    
    if file:
        soup = BeautifulSoup(file, 'html.parser')
    
    else:
        soup = BeautifulSoup(driver.page_source, 'html.parser')

    table_senate = soup.find('div', {'id': "State Senate Scorecard"}).table
    table_house = soup.find('div', {'id': "State House Scorecard"}).table

    return extract_table(table_senate) + extract_table(table_house)


def download_page(driver:webdriver.Chrome):

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    HTML_FILES.mkdir(exist_ok=True)

    with open(HTML_FILES / f"{FILENAME}_{TIMESTAMP}.html", 'w') as f:
        f.write(soup.prettify())


def extract_from_file(files:list):

    extracted  = []

    for file in files:

        with open(file, 'r') as f:
            file_contents = f.read()
        
        extracted += extract(driver=None, file=file_contents)
    
    EXTRACT_FILES.mkdir(exist_ok=True)

    df = pandas.DataFrame.from_records(extracted)
    df.to_csv(EXTRACT_FILES / f"{FILENAME}-Extract_{TIMESTAMP}.csv", index=False)


def main():

    chrome_service = Service('chromedriver')
    chrome_options = Options()
    chrome_options.add_argument('incognito')
    chrome_options.add_argument('headless')
    chrome_driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    chrome_driver.get(URL)
    
    extracted = extract(chrome_driver)
    download_page(chrome_driver)

    EXTRACT_FILES.mkdir(exist_ok=True)
    df = pandas.DataFrame.from_records(extracted)
    df.to_csv(EXTRACT_FILES / f"{FILENAME}-Extract_{TIMESTAMP}.csv", index=False)


if __name__ == "__main__":
    _, EXPORT_DIR, *FILES = sys.argv

    EXPORT_DIR = Path(EXPORT_DIR)
    HTML_FILES = EXPORT_DIR / "HTML_FILES"
    EXTRACT_FILES = EXPORT_DIR / "EXTRACT_FILES"

    if FILES:
        extract_from_file(FILES)
    else:
        main()
