# This is the webscraping script for Massachusetts Society for the Prevention of Cruelty to Animals, sig_id = 1204


import sys
import pandas

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path


FILENAME = "_MA_MSPCA_Ratings"
TIMESTAMP = datetime.strftime(datetime.now(), '%Y-%m-%d')


def extract(driver:webdriver.Chrome, file:str=None):

    if file:
        soup = BeautifulSoup(file, 'html.parser')
    else:
        soup = BeautifulSoup(driver.page_source, 'html.parser')

    table = soup.find('table', {'class':'votertable'})
    headers = ['office','name'] + [th.text.strip() for th in table.thead.find_all('th')[2:]]
    rows = [tr.find_all('td') for tr in table.tbody.find_all('tr')]

    get_text = lambda x: x.text.strip()

    return [dict(zip(headers, map(get_text, row))) for row in rows]


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
    _, EXPORT_DIR, URL, *FILES= sys.argv

    EXPORT_DIR = Path(EXPORT_DIR)
    HTML_FILES = EXPORT_DIR / "HTML_FILES"
    EXTRACT_FILES = EXPORT_DIR / "EXTRACT_FILES"

    if FILES:
        extract_from_file(FILES)
    else:
        main()

