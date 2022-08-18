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


MAIN_URL = "http://ratings.conservative.org/people"
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
GROUP_ABV = 'ACU'

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
    param_dict = {p.split('=')[0]:p.split('=')[1] for p in params}

    if param and param in param_dict.keys():
        return param_dict[param]


def extract(driver):

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    candidates = soup.find_all('div', {'class': 'sc-hzDkRC'})
    level = get_url_param(driver.current_url, 'state')

    records = []
    
    for c in candidates:

        acu_id = c.a['href'].split('/')[-1].strip()
        name_party, office_state_district = c.find('div', {'class':'sc-fBuWsC'}).find_all('p')
        name = ''.join(name_party.text.split('(')[:1]).strip()
        party = ''.join(name_party.text.split('(')[1:]).strip(') ')
        osd_split = office_state_district.text.split('-')

        office = osd_split[0].strip() if osd_split else ''
        state_id = osd_split[1].strip() if len(osd_split) > 1 else ''
        district = osd_split[2].strip() if len(osd_split) > 2 else ''

        score = c.find('div', {'class':'sc-gPEVay'})

        records.append({'acu_id': acu_id,
                        'name': name,
                        'party': party,
                        'office': office,
                        'state_id': state_id if district else None,
                        'district:': district if district else state_id,
                        'score': score.text if score else '',
                        'level': level})

    return records


def download_page(driver):

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    level = get_url_param(driver.current_url, 'state')
    year = get_url_param(driver.current_url, 'year')

    if not os.path.isdir(f"{SCRIPT_DIR}/ACU_HTML"):
        os.mkdir(f"{SCRIPT_DIR}/ACU_HTML")

    with open(f"{SCRIPT_DIR}/ACU_HTML/{year}_NA_ACU_Ratings_{level}-{datetime.now().strftime('%Y-%m-%d')}.html", 'w') as f:
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
