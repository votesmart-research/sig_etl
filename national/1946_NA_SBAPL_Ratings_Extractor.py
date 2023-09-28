# This is the webscraping script for Susan B. Anthony List, sig_id = 1946

from pathlib import Path
from datetime import datetime

import pandas
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select


URL = "https://sbaprolife.org/scorecard"


def extract(page_source):
    soup = BeautifulSoup(page_source, 'html.parser')

    table_senate = soup.find('table', {'id': 'sc_dt_sen'})
    table_house = soup.find('table', {'id': 'sc_dt_house'})

    def extract_table(table):
        headers = [th.get_text(strip=True)
                   for th in table.thead.find_all('th')]
        rows = [tr.find_all('td') for tr in table.tbody.find_all('tr')]
        def get_text(x): return x.get_text(strip=True)

        return [dict(zip(headers, map(get_text, row))) for row in rows]
    
    return extract_table(table_senate) + extract_table(table_house)


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
        options=chrome_options, service=chrome_service)
    chrome_driver.get(URL)

    senate_entries = Select(chrome_driver.find_element(
        By.XPATH, "//select[@name='sc_dt_sen_length']"))
    senate_entries.select_by_value('100')

    house_entries = Select(chrome_driver.find_element(
        By.XPATH, "//select[@name='sc_dt_house_length']"))
    house_entries.select_by_value('100')

    extracted = []

    while True:
        senate_next = chrome_driver.find_element(By.ID, "sc_dt_sen_next")
        house_next = chrome_driver.find_element(By.ID, "sc_dt_house_next")

        for record in extract(chrome_driver.page_source):
            if record not in extracted:
                extracted.append(record)

        save_html(chrome_driver.page_source, EXPORT_DIR)

        if not 'disabled' in senate_next.get_attribute('class'):
            senate_next.find_element(By.TAG_NAME, "a").click()

        elif not 'disabled' in house_next.get_attribute('class'):
            house_next.find_element(By.TAG_NAME, "a").click()

        else:
            break
    
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