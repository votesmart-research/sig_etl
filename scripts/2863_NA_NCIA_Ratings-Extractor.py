# This is the webscraping script for National Cannabis Industry Association (NCIA), sig_id=2863

import requests
import pandas
import os
import re

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from tqdm import tqdm
from datetime import datetime


MAIN_URL = "https://thecannabisindustry.org/ncia-news-resources/congressional-scorecards"
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
GROUP_ABV = 'NCIA'


def extract(response):

    records = []
    candidate_soup = BeautifulSoup(response.text, 'html.parser')
    rep_cards = candidate_soup.find('section', {'class': 'scorecards'}).find_all('div', {'class': 'rep'})
    state = response.url.strip('/').split('/')[-1].capitalize()
    for rep_card in rep_cards:
        
        scores = rep_card.find('div', {'class': 'score'}).find_all('h3')
        rating = '/'.join(map(lambda x: x.text, scores)) if scores else None
        info  = rep_card.find('div', {'class': 'info'})
        party = info.find('h5', {'class': 'party'})
        name = info.find('h3')
        
        if party.span:
            district = party.span.text
            party.span.decompose()
        
        else:
            district = None

        records.append({'name': name.text if name else None,
                        'state': state,
                        'party': party.text if party else None,
                        'district': district,
                        'sig_rating': rating})

    return records


def download_page(response):

    soup = BeautifulSoup(response.text, 'html.parser')
    state = response.url.strip('/').split('/')[-1].capitalize()

    if not os.path.isdir(f"{SCRIPT_DIR}/NCIA_HTML"):
        os.mkdir(f"{SCRIPT_DIR}/NCIA_HTML")

    with open(f"{SCRIPT_DIR}/{GROUP_ABV}_HTML/_NA_NCIA_Ratings_{state}.html", 'w') as f:
        f.write(soup.prettify())


def main():

    chrome_service = Service('chromedriver')
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('incognito')

    driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
    driver.get(MAIN_URL)

    try:
        WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, "//div[@id='mapdivc']/div/div/svg")))

    except TimeoutException:
        print("ERROR. Page did not load.")
        driver.quit()
        exit()

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    paths = soup.find('div', {'id': 'mapdivc'}).find_all('path')

    all_records = []

    for path in tqdm(paths):

        if path and 'aria-label' in path.attrs.keys():
            pass
        else:
            continue

        state = re.sub('\s\d+\s', '', path['aria-label'])
        response = requests.get(f"{MAIN_URL}/{state}")
        all_records += extract(response)
        download_page(response)

    df = pandas.DataFrame.from_records(all_records)
    df.to_csv(f"_NA_{GROUP_ABV}_Ratings-Extract_{datetime.now().strftime('%Y-%m-%d')}.csv", index=False)


if __name__ == "__main__":
    main()
