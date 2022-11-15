# This is the webscraping script for Heritage Action for America, sig_id=2061

import pandas
import os
import sys

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
from tqdm import tqdm


MAIN_URL = "https://heritageaction.com/scorecard/members"


def extract(driver):

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    heritage_id = driver.current_url.split('/')[-2]

    name = soup.find('h1', {'class': 'text-2xl'})
    info = soup.find_all('span', {'class':'uppercase'})

    scores = soup.find_all('div', {'class': 'member-stats__item'})
    scores_text = {score.span.text.strip(): score.div.text.strip() for score in scores[:2]}

    return  {'heritage_id': heritage_id,
            'name': name.text.strip() if name else None,
            'party': info[0].text.strip() if info else None,
            'state_district': info[1].text.strip() if len(info) > 1 else ""} | scores_text   



def download_page(driver):

    if not os.path.isdir(f"{EXPORT_DIR}/HTML_FILES"):
        os.mkdir(f"{EXPORT_DIR}/HTML_FILES")

    session = driver.current_url.split('/')[-1]
    candidate_id = driver.current_url.split('/')[-2]
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    with open(f'{EXPORT_DIR}/HTML_FILES/{session}_Ratings_{candidate_id}.html', 'w') as f:
        f.write(soup.prettify())


def main():
    chrome_service = Service('chromedriver')
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('incognito')
    chrome_options.add_argument('headless')

    driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
    driver.get(MAIN_URL)
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    candidate_urls = [tr.a['href'] for tr in soup.tbody.find_all('tr')]

    records = []

    for url in tqdm(candidate_urls):

        driver.get(f'https://heritageaction.com{url}')
        records.append(extract(driver))
        download_page(driver)

    df = pandas.DataFrame.from_records(records)
    df.to_csv(f'{EXPORT_DIR}/_NA_Heritage_Ratings-Extract.csv', index=False)


if __name__ == '__main__':
    _, EXPORT_DIR = sys.argv
    main()