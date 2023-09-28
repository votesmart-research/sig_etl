# This is the webscraping script for American Energy Alliance (AEA), sig_id=2526

from datetime import datetime
from pathlib import Path

import pandas
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options


URL = "https://www.americanenergyalliance.org/american-energy-scorecard/?spage=overall"


def extract(page_source):

    soup = BeautifulSoup(page_source, 'html.parser')
    table = soup.find('div', {'class': 'membersTable'}).table

    headers = [th.get_text(strip=True) for th in table.thead.find_all('th')]
    rows = [tr.find_all('td') for tr in table.tbody.find_all('tr')]

    def get_text(x): return x.get_text(strip=True)

    return [dict(zip(headers, map(get_text, row))) for row in rows]


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
    save_html(chrome_driver.page_source, EXPORT_DIR)

    extracted = extract(chrome_driver.page_source)
    save_extract(extracted, EXPORT_DIR)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(prog='sig_webscrape')
    parser.add_argument(
        'exportdir', help='file directory of where the files exports to')
    parser.add_argument('-f', '--htmldir', help='file directory of html files')

    args = parser.parse_args()

    EXPORT_DIR = Path(args.exportdir)

    main()
