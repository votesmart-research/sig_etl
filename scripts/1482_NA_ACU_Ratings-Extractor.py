# This is the webscraping script for American Conservative Union (ACU), sig_id=1482

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
from tqdm import tqdm


GROUP_ABV = 'ACU'
SIG_COVERAGE = 'NA'
MAIN_URL = "http://ratings.conservative.org/people"
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
URL_FILTERS = {'year': 'year=',
               'state': 'state=',
               'party': 'party=',
               'office': 'chamber=',
               'limit': 'limit=',
               'level': 'level='}
STATES = ['AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 
          'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 
          'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'US']


def apply_url_filter(**filters):
    f = '&'.join([URL_FILTERS[k] + v for k, v in filters.items()])
    return '?'.join([MAIN_URL, f])


def get_url_param(url, param=None):
    params = url.split('?')[1].split('&')
    params_dict = {p.split('=')[0]:p.split('=')[1] for p in params}

    if param and param in params_dict.keys():
        return params_dict[param]


def extract(driver):

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    candidates = soup.find_all('div', {'class': 'sc-hzDkRC'})
    geo_coverage = get_url_param(driver.current_url, 'state')

    records = []
    
    for candidate in candidates:

        name_party, office_state_district = candidate.find('div', {'class':'sc-fBuWsC'}).find_all('p')
        rating = candidate.find('div', {'class':'sc-gPEVay'})

        # name = ''.join(name_party.text.split('(')[:1]).strip()
        # party = ''.join(name_party.text.split('(')[1:]).strip(') ')
        # osd_split = office_state_district.text.split('-')
        # office = osd_split[0].strip() if osd_split else ''
        # state_id = osd_split[1].strip() if len(osd_split) > 1 else ''
        # district = osd_split[2].strip() if len(osd_split) > 2 else ''

        records.append({'sig_candidate_id': candidate.a['href'].split('/')[-1].strip(),
                        'name_party': name_party,
                        'office_state': office_state_district.a.text,
                        'district:': office_state_district.a.next_sibling,
                        'rating': rating.text,
                        'geo_coverage': geo_coverage})

    return records


def download_page(driver):

    foldername = f"{GROUP_ABV}_HTML"

    if not os.path.isdir(f"{SCRIPT_DIR}/{foldername}"):
        os.mkdir(f"{SCRIPT_DIR}/{foldername}_HTML")

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    geo_coverage = get_url_param(driver.current_url, 'state')
    year = get_url_param(driver.current_url, 'year')

    filename = f"{year}_NA_{GROUP_ABV}_Ratings_{geo_coverage}-{datetime.now().strftime('%Y-%m-%d')}.html"

    with open(f"{SCRIPT_DIR}/{foldername}/{filename}", 'w') as f:
        f.write(soup.prettify())


def main():

    chrome_service = Service('chromedriver')
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('incognito')
    
    driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    records = []

    for state in tqdm(STATES):

        filtered_URL = apply_url_filter(year=YEAR, state=state, limit='all', level='state')
        driver.get(filtered_URL)

        try:
            WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, "//div[@class='sc-cEvuZC jdbFxJ']")))

        except TimeoutException:
            print(f"{state} has a timeout.")
            continue

        extracted =  extract(driver)

        if extracted:
            records += extracted
            download_page(driver)
            
    driver.quit()

    df = pandas.DataFrame.from_records(records)
    df.to_csv(f"{YEAR}_NA_ACU_Ratings-Extract_{datetime.now().strftime('%Y-%m-%d')}.csv", index=False)


if __name__ == '__main__':
    script, YEAR = sys.argv

    main()
