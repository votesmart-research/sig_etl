# This is the webscraping script for National Parks Conservation Association (NPCA), sig_id=922

import os
import pandas
import sys

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from tqdm import tqdm
from bs4 import BeautifulSoup


MAIN_URL = "https://nationalparksaction.org/online-scorecard/"


def candidate_urls(soup):
    container = soup.find('div', {'id': 'legislators-container'})
    urls = [card.a['href'] for card in container.find_all('div', {'class': 'card'})]

    return urls


def extract(driver):
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    npca_id = driver.current_url.split('/')[-1]
    name = soup.find('div', {'class': 'legislator-name'})

    info = soup.find('div', {'class': 'legislator-sub-head'})
    score_containers = soup.find_all('p', {'class': 'legislator-detail-score'})

    score_headers = [p.strong.text.strip() for p in score_containers]
    scores = [p.span.text.strip() for p in score_containers]

    record = {'NPCA_id': npca_id,
              'name': name.text.strip() if name else None, 
              'info': info.text.strip() if info else None} | dict(zip(score_headers, scores))

    return record


def download_page(driver):
    if not os.path.isdir(f"{EXPORTDIR}/HTML_FILES"):
        os.mkdir(f"{EXPORTDIR}/HTML_FILES")

    candidate_id = driver.current_url.split('/')[-1]
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    with open(f"{EXPORTDIR}/HTML_FILES/Ratings_{candidate_id}.html", 'w') as f:
        f.write(soup.prettify())


def main():
    chrome_service = Service('chromedriver')
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('incognito')
    # chrome_options.add_argument('headless')

    driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    driver.get(MAIN_URL)

    try:
        WebDriverWait(driver,10).until(EC.presence_of_element_located((By.ID, "legislators-container")))
        
    except TimeoutException:
        print("Cannot find Legislator Container. Quitting...")
        exit()


    while True:
        try:
            pagination = driver.find_element(By.XPATH, "//div[@class='pagination pure-u-md-1 pure-u-lg-3-4']/a")

            if pagination:
                pagination.click()
            else:
                break

        except NoSuchElementException:
            break

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    records = []

    for url in tqdm(candidate_urls(soup)):
        driver.get(MAIN_URL + url)
        records.append(extract(driver))
        download_page(driver)

    df = pandas.DataFrame.from_records(records)
    df.to_csv(f'{EXPORTDIR}/_NA_NPCA_Ratings-Extract.csv', index=False)

if __name__ == '__main__':
    _, EXPORTDIR = sys.argv
    EXPORTDIR = EXPORTDIR if os.path.isdir(EXPORTDIR) else os.path.dirname(EXPORTDIR)

    main()