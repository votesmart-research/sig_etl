# This is the webscraping script for Animal Welfare Institute (AWI), sig_id=1574

import time
import pandas
import sys

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from bs4 import BeautifulSoup


URL = "https://awionline.org/compassion-index#/legislators"

TO_SELECT = ['117-Senate', '117-House']


def extract(soup):

    rows = soup.table.tbody.find_all('tr')

    records = []
    
    for tr in rows[1:]:
        info, rating = tr.find_all('td')

        name = info.a if info else None
        party_state_district = info.find('div', {'class': 'congressweb-legislator-sub-content'}) if rating else None

        records.append({'name': name.text.strip() if name else None,
                        'party-state-district': party_state_district.text.strip() if party_state_district else None,
                        'score': rating.text.strip()})

    return records


def download_page(driver, session):
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    with open(f'{EXPORTDIR}/{session}_NA_AWI_Ratings.html', 'w') as f:
        f.write(soup.prettify())


def main():

    chrome_service = Service('chromedriver')
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('incognito')
    driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
    driver.get(URL)

    combined_records = []

    for session in TO_SELECT:

        driver.refresh()

        time.sleep(3)

        iframe = driver.find_element(By.TAG_NAME, 'iframe')
        driver.switch_to.frame(iframe)

        select_congress = Select(driver.find_element(By.XPATH, "//select[@name='congress_chamber']"))
        button_congress = driver.find_element(By.XPATH, "//form[@action='/AWI/legislators/membercompassionindex']//input")
        
        select_congress.select_by_value(session)
        button_congress.click()

        time.sleep(3)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        download_page(driver, session)
        
        combined_records += extract(soup)

        time.sleep(3)

    df = pandas.DataFrame.from_records(combined_records)
    df.to_csv(f'{EXPORTDIR}/_NA_AWI_Ratings-Extract.csv', index=False)
        

if __name__ == '__main__':
    _, EXPORTDIR = sys.argv
    main()