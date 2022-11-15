# This is the webscraping script for Progressive Punch, sig_id=2167

import os
import sys
import pandas

from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service


URL = "https://www.progressivepunch.org/scores.htm"
TIMESTAMP = datetime.now().strftime('%Y-%m-%d')


def extract(soup):
    header_section, body = soup.find_all('table', {'id': 'all-members'})
    
    info_headers = header_section.find('tr', {'class': 'heading'}).find_all('td')
    sub_headers = header_section.find('tr', {'class': 'subheading'}).find_all('td')

    header_text = list(map(lambda td: td.text.strip() if td else None, info_headers[:4] + sub_headers[6:8]))

    rows = body.find_all('tr')

    records = []

    for row in rows:
        columns = row.find_all('td')
        column_text = [td.text.strip() for td in columns[:4] + columns[6:8]]
        records.append(dict(zip(header_text, column_text)))

    return records


def download_page(driver):

    if not os.path.isdir(f"{EXPORT_DIR}/HTML_FILES"):
        os.mkdir(f"{EXPORT_DIR}/HTML_FILES")

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    filename = "_NA_ProgressivePunch_Ratings_{TIMESTAMP}.html"

    with open(f"{EXPORT_DIR}/HTML_FILES/{filename}", 'w') as f:
        f.write(soup.prettify())


def main():

    chrome_service = Service('chromedriver')
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('incognito')
    chrome_options.add_argument('headless')
    driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    driver.get(URL)
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    records = extract(soup)
    download_page(driver)

    df = pandas.DataFrame.from_records(records)
    df.to_csv(f"{EXPORT_DIR}/_NA_ProgressivePunch_Ratings-Extract_{TIMESTAMP}.csv", index=False)


if __name__ == "__main__":
    _, EXPORT_DIR = sys.argv
    main()

