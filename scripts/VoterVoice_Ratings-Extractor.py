# This is a webscraping script for groups who uses Voter Voice.

import sys
import os
import pandas

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from datetime import datetime
from collections import defaultdict


RATINGS_METHODOLOGY = {'Voted with us': '+',
                       'Voted against us': '-',
                       'No position': '*',
                        None: ''}

# def extract_table(table):

#     header = [th.text for th in table.thead.find_all('th')]
#     rows = [tr.find_all('td') for tr in table.tbody.find_all('tr')]

#     get_text = lambda x: x.text.strip()

#     return [dict(zip(header, map(get_text, row))) for row in rows]


def extract(driver):

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    office = soup.find('div', {'class':'vv-tab-menu-item-active'}).text.strip()
    sessions = soup.find_all('section', {'class':'vv-scorecard-section'})

    def _extract(row):
        columns = row.find_all('td')
        rating_string = [td.span['title'] if td.span else None for td in columns[2:]]
        translated_rating_string = "".join([RATINGS_METHODOLOGY[c] for c in rating_string])

        return {'name_party_state': columns[0]['title'],
                'rating': columns[1].text,
                'rating_string': translated_rating_string,
                'office': office,
                }

    for session in sessions:
        span = session.header.text.strip() 
        rows = session.table.tbody.find_all('tr')
        yield span, [_extract(row) for row in rows]


def export_records(session_records):

    with pandas.ExcelWriter(f"{SCRIPT_DIR}/_NA_{GROUP_ABV}_Ratings-Extract.ods") as writer:
        for session, records in session_records.items():
            if records:
                pandas.DataFrame.from_records(records).to_excel(writer, sheet_name=session, index=False)


def download_page(driver):

    if not os.path.isdir(f"{SCRIPT_DIR}/HTML_FILES"):
        os.mkdir(f"{SCRIPT_DIR}/HTML_FILES")

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    office = soup.find('div', {'class':'vv-tab-menu-item-active'}).text.strip()
    timestamp = datetime.now().strftime('%Y-%m-%d')

    with open(f"{SCRIPT_DIR}/HTML_FILES/Ratings_{office}-{timestamp}.html", 'w') as f:
        f.write(soup.prettify())


def main():
    
    # chrome_service = Service('chromedriver')
    # chrome_options = webdriver.ChromeOptions()
    # chrome_options.add_argument('incognito')
    # driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    edge_service = Service('msedgedriver')
    edge_options = webdriver.EdgeOptions()
    edge_options.add_argument('inprivate')
    driver = webdriver.Edge(service=edge_service, options=edge_options)

    driver.get(MAIN_URL)

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, '//table[@class="vvScorecardAggregate"]/tbody/tr'))
        )
    except TimeoutException:
        print("An error occurred: The page could not load.")
        driver.quit()
        exit()

    offices = driver.find_elements(By.XPATH, '//section[@id="vvConsolidatedScorecardResults"]//div[@class="vv-tab-menu-item-container"]')
    records_by_session = defaultdict(list)

    for office in offices:
        office.click()

        for session, records in extract(driver):
                records_by_session[session] += records

        download_page(driver)

    export_records(records_by_session)


if __name__ == '__main__':

    script, MAIN_URL = sys.argv

    GROUP_ABV = MAIN_URL.split('/')[4]
    SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

    main()
