# This is the web-scraping script for Maine People's Alliance, sig_id=26

import os
import sys
import pandas

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

from bs4 import BeautifulSoup
from datetime import datetime
from tqdm import tqdm


URL = "https://mpascorecard.org"
FILENAME = "26_ME_MPA_Ratings"
TIMESTAMP = datetime.strftime(datetime.now(), '%Y-%m-%d')

WEBARCHIVE_URL = "https://web.archive.org"

def get_candidate_urls(driver:webdriver.Chrome):
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    return [div.a['href'] for div in soup.find_all('div', {'class':'legislator-name'})]


def click_legislator(driver:webdriver.Chrome, pos):
    legislators = driver.find_elements(By.CLASS_NAME, 'legislator-name')
    legislators[pos].find_element(By.TAG_NAME, 'a').click()


def extract(driver:webdriver.Chrome):
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    name = soup.find('div', {'class': 'legislator-name'})
    party_county = soup.find('div', {'class': 'legislator-subtitle'})
    district = soup.find('section', {'class': 'district-info'}).find('div', {'class': 'title'})
    score_year = soup.find('div', 'mpa-score').h1
    score = soup.find('div', 'mpa-score').find('div', {'class':'number'})
    
    return {'name': name.text.strip() if name else None,
            'party_county': party_county.text.strip() if party_county else None,
            'district': district.text.strip() if district else None,
             score_year.text.strip() if score_year else None: score.text.strip() if score else None}


def download_page(driver:webdriver.Chrome):

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    candidate_name = driver.current_url.strip('/').split('/')[-1]
    
    if not os.path.exists(HTML_FILES):
        os.mkdir(HTML_FILES)

    filename = f"{FILENAME}_{candidate_name}-{TIMESTAMP}.html"
    
    with open(f"{HTML_FILES}/{filename}", 'w') as f:
        f.write(soup.prettify())


def main():
    
    chrome_service = Service('chromedriver')
    chrome_options = Options()
    chrome_options.add_argument('incognito')
    chrome_options.add_argument('headless')

    chrome_driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    records = []

    ## Regular Extraction
    chrome_driver.get(f"{URL}/all-scores")

    for url in tqdm(get_candidate_urls(chrome_driver)):
        chrome_driver.get(f"{URL}{url}")
        download_page(chrome_driver)
        records.append(extract(chrome_driver))


    ## WEBARCHIVE method of extraction
    # chrome_driver.get(f"{WEBARCHIVE_URL}/web/20211205142851/https://mpascorecard.org/all-scores/")
    # counter = 0
    # max_count = len(chrome_driver.find_elements(By.CLASS_NAME, 'legislator-name'))
    # pbar = tqdm(total=max_count)

    # while counter < max_count:

    #     click_legislator(chrome_driver, counter)

    #     download_page(chrome_driver)
    #     records.append(extract(chrome_driver))

    #     container = chrome_driver.find_element(By.XPATH, "//div[@id='root']//nav[@class='container']")
    #     container_links = container.find_elements(By.TAG_NAME, 'a')
    #     container_links[3].click()

    #     pbar.update(1)
    #     counter += 1

    df = pandas.DataFrame.from_records(records)
    df.to_csv(f"{EXPORT_DIR}/{FILENAME}-Extract_{TIMESTAMP}.csv", index=False)


if __name__ == '__main__':
    _, EXPORT_DIR = sys.argv
    HTML_FILES = f"{EXPORT_DIR}/HTML_FILES"
    main()