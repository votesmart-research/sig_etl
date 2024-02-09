# This is the webscraping script for Progressive Punch, sig_id=2167

import sys
from pathlib import Path
from datetime import datetime

import pandas
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options


URL = "https://www.progressivepunch.org/scores.htm"


def extract(page_source):
    soup = BeautifulSoup(page_source, 'html.parser')

    header_section, body = soup.find_all('table', {'id': 'all-members'})

    info_headers = header_section.find(
        'tr', {'class': 'heading'}).find_all('td')
    sub_headers = header_section.find(
        'tr', {'class': 'subheading'}).find_all('td')

    header_text = [td.get_text(strip=True) if td else None
                   for td in info_headers[:4] + sub_headers[6:8]]

    records = []

    for row in body.find_all('tr'):
        columns = row.find_all('td')
        column_text = [td.get_text(strip=True)
                       for td in columns[:4] + columns[6:8]]
        records.append(dict(zip(header_text, column_text)))

    return records


def save_html(page_source, filepath, *additional_info):

    soup = BeautifulSoup(page_source, 'html.parser')

    filepath = Path(filepath) / 'HTML_FILES'
    filepath.mkdir(exist_ok=True)

    timestamp = datetime.strftime(datetime.now(), '%Y-%m-%d-%H%M%S-%f')

    with open(filepath / f"Ratings_{'-'.join(map(str, additional_info))}"
                         f"{'-' if additional_info else ''}{timestamp}.html", 'w') as f:
        f.write(str(soup))


def save_extract(extracted: dict[dict], filepath, *additional_info):

    filepath = Path(filepath) / 'EXTRACT_FILES'
    filepath.mkdir(exist_ok=True)

    timestamp = datetime.strftime(datetime.now(), '%Y-%m-%d-%H%M%S-%f')

    df = pandas.DataFrame.from_records(extracted)
    df.to_csv(
        filepath / f"Ratings-Extract_{'-'.join(map(str, additional_info))}"
                   f"{'-' if additional_info else ''}{timestamp}.csv", index=False)


def main():

    chrome_service = Service('chromedriver')
    chrome_options = Options()
    chrome_options.add_argument('incognito')
    chrome_options.add_argument('headless')
    chrome_driver = webdriver.Chrome(
        service=chrome_service, options=chrome_options)

    chrome_driver.get(URL)

    records = extract(chrome_driver.page_source)

    save_extract(records, filepath=EXPORT_DIR)
    save_html(chrome_driver.page_source, filepath=EXPORT_DIR)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(prog='sig_webscrape')
    parser.add_argument(
        'exportdir', help='file directory of where the files exports to')
    parser.add_argument('-f', '--htmldir', help='file directory of html files')

    args = parser.parse_args()

    EXPORT_DIR = Path(args.exportdir)

    main()
