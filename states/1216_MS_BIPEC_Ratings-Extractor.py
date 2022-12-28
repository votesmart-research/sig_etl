# This is the webscraping script for Business & Industry Political Education Committee, sig_id = 1216

import os
import sys
import pandas

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
from datetime import datetime


YEAR = 2020
URL = f"https://www.bipec.org/reportcards/{YEAR}"
FILENAME = "1216_MA_BIPEC_Ratings"
TIMESTAMP = datetime.strftime(datetime.now(), '%Y-%m-%d')

METHODOLOGY = {'glyphicon-ok': '+', 
               'glyphicon-remove': '-'}

OFFICES = ['house', 'senate']


def extract(driver):

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    table = soup.find('table', {'id': 'example'})
    office = driver.current_url.split('=')[-1]

    headers = []

    for th in table.thead.find_all('th'):
        if th.span:
            th.span.clear()
        headers.append(th.text)

    rows = [tr.find_all('td') for tr in table.tbody.find_all('tr')]

    records = []
    
    for row in rows:
        bipec_id = row[1].a['href'].split('=')[-1]
        
        translate_rating = lambda x: METHODOLOGY[x.span['class'][-1]] if x.span else x.text

        records.append({'bipec_id': bipec_id} |
                        dict(zip(headers[:4], map(lambda x: x.text.strip(), row[:4]))) | 
                        {'office': office} |
                        dict(zip(headers[4:], map(translate_rating, row[4:])))
                        )
    return records


def download_page(driver):
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    office = driver.current_url.split('=')[-1]

    if not os.path.isdir(HTML_FILES):
        os.mkdir(HTML_FILES)

    with open(f"{HTML_FILES}/{FILENAME}_{office}-{TIMESTAMP}.html", 'w') as f:
        f.write(soup.prettify())


def main():
    
    chrome_service = Service('chromedriver')
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('incognito')
    chrome_options.add_argument('headless')

    driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    extracted = []

    for office in OFFICES:
        driver.get(f"{URL}/?c={office}")
        
        download_page(driver)
        extracted += extract(driver)

    df = pandas.DataFrame.from_records(extracted)
    df.to_csv(f"{EXPORT_DIR}/{FILENAME}-Extract_{TIMESTAMP}.csv", index=False)


if __name__ == "__main__":
    _, EXPORT_DIR = sys.argv
    HTML_FILES = f"{EXPORT_DIR}/HTML_FILES"
    main()
