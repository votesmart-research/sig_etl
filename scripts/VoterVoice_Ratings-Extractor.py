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


SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
RATINGS_METHODOLOGY = {'Voted with us': '+',
                       'Voted against us': '-',
                       'No position': '*',
                        None: ''}


def extract(driver):

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    office = soup.find('div', {'class':'vv-tab-menu-item-active'}).text.strip()
    sessions = soup.find_all('section', {'class':'vv-scorecard-section'})

    def _extract(row):
        columns = row.find_all('td')
        info = columns[0]['title'].strip().split('(')
        party, state_id, *district = info[-1].split('-')
        score = columns[1].text.strip()
        rating_string = [td.span['title'] if td.span else None for td in columns[2:]]
        translated_ratings = "".join([RATINGS_METHODOLOGY[c] for c in rating_string])

        return {'name': info[0].strip(),
                'office': office,
                'state_id': state_id.strip(')'),
                'district': "".join(district).strip(')'),
                'party': party,
                'ratings': translated_ratings,
                'score': score}

    session_records = {}

    for session in sessions:
        span = session.header.text.strip() 
        rows = session.table.tbody.find_all('tr')
        session_records[span] = [_extract(row) for row in rows]

    return session_records


def records_to_sheet(session_records):

    with pandas.ExcelWriter(f"{SCRIPT_DIR}/_NA_{GROUP_ABV}_Ratings-Extract.ods") as writer:
        for session, records in session_records.items():
            if records:
                pandas.DataFrame.from_records(records).to_excel(writer, sheet_name=session, index=False)


def download_page(driver):

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    office = soup.find('div', {'class':'vv-tab-menu-item-active'}).text.strip()
    timestamp = datetime.now().strftime('%Y-%m-%d')

    if not os.path.isdir(f"{SCRIPT_DIR}/{GROUP_ABV}_HTML"):
        os.mkdir(f"{SCRIPT_DIR}/{GROUP_ABV}_HTML")

    with open(f"{SCRIPT_DIR}/{GROUP_ABV}_HTML/_NA_{GROUP_ABV}_Ratings_{office}-{timestamp}.html", 'w') as f:
        f.write(soup.prettify())


def main():
    
    chrome_service = Service('chromedriver')
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('incognito')

    driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
    driver.get(MAIN_URL)

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, '//table[@class="vvScorecardAggregate"]/tbody/tr'))
        )
    except TimeoutException:
        print("ERROR. Page did not load.")
        driver.quit()
        exit()

    offices = driver.find_elements(By.XPATH, '//section[@id="vvConsolidatedScorecardResults"]//div[@class="vv-tab-menu-item-container"]')
    all_records = defaultdict(list)

    for office in offices:
        office.click()

        for session, records in extract(driver).items():
                all_records[session] += records

        download_page(driver)

    records_to_sheet(all_records)


if __name__ == '__main__':

    script, MAIN_URL = sys.argv
    GROUP_ABV = MAIN_URL.split('/')[4]

    main()
