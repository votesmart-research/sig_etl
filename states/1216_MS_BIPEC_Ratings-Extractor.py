# This is the webscraping script for Business & Industry Political Education Committee, sig_id = 1216

import os
import sys
import pandas

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup


YEAR = 2022
URL = "https://www.bipec.org/reportcards/{YEAR}"
METHODOLOGY = {'glyphicon-ok': '+', 
               'glyphicon-remove': '-'}


def get_table(driver):
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    table = soup.find('table', {'id': 'example'})

    return table


def extract(table):

    header = [th.text for th in table.thead.find_all('th')]
    rows = [tr.find_all('td') for tr in table.tbody.find_all('tr')]

    records = []
    
    for row in rows:
        records.append(dict(zip(header[:4], map(lambda x: x.text.strip(), row[:4]))) | 
                       dict(zip(header[4:], map(lambda x: METHODOLOGY[x], row[4:]))))
        
    return records


def download_page(driver):
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    office = driver.current_url.split('=')[-1]

    if not os.path.isdir(f"{EXPORT_DIR}/HTML_FILES"):
        os.mkdir(f"{EXPORT_DIR}/HTML_FILES")

    with open(f"{EXPORT_DIR}/HTML_FILES/_MS_BIPEC_Ratings_{office}.html", 'w') as f:
        f.write(soup.prettify())


def main():
    
    chrome_service = Service('chromedriver')
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('incognito')
    chrome_options.add_argument('headless')

    driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    driver.get(f"{URL}/href=?c=house")
    table_house = get_table(driver)

    driver.get(f"{URL}/href=?c=senate")
    table_senate = get_table(driver)

    extract(table_house)

    # df = pandas.DataFrame.from_records(extracted)
    # df.to_csv(f"{EXPORT_DIR}/_MS_BIPEC_Ratings-Extract.csv", index=False)


if __name__ == "__main__":
    _, EXPORT_DIR = sys.argv
    main()
