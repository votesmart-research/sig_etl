# This is webscraping script for SIGS that uses BillTrack50 scorecardapp

import sys
import pandas
import re

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (TimeoutException,
                                        NoSuchElementException,
                                        ElementClickInterceptedException)

from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from tqdm import tqdm
from urllib.parse import urljoin
from collections import defaultdict


def extract(driver: webdriver.Chrome, file: str = None, **columns):

    if file:
        soup = BeautifulSoup(file, 'html.parser')
    else:
        # sometimes webpage might take a while to load
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located(
                (By.XPATH, "//div[@class='legislator-detail']")))
        except TimeoutException:
            pass
        soup = BeautifulSoup(driver.page_source, 'html.parser')

    last_segment_match = re.search(
        r"/+([^\W_]\w*)\W*$", driver.current_url) if driver else None
    sig_candidate_id = last_segment_match.group(
        1) if last_segment_match else ""

    name = soup.find('div', {'class': 'legislator-name'})
    info = soup.find('div', {'class': 'legislator-sub-head'})
    score_containers = soup.find_all('p', {'class': 'legislator-detail-score'})

    score_headers = [p.strong.text.strip() for p in score_containers]
    scores = [p.span.text.strip() for p in score_containers]

    return {'sig_candidate_id': sig_candidate_id,
            'name': name.text.strip() if name else None,
            'info': info.text.strip() if info else None} \
        | dict(zip(score_headers, scores)) \
        | columns if columns else {} \



def extract_card(driver: webdriver.Chrome, file: str = None):

    if file:
        soup = BeautifulSoup(file, 'html.parser')
    else:
        soup = BeautifulSoup(driver.page_source, 'html.parser')

    container = soup.find('div', {'id': 'legislators-container'})

    extracted = defaultdict(dict)

    for card in container.find_all('div', {'class': 'card'}):
        url = card.find('a')['href']
        score = card.find('div', {'class': 'score'})
        party = card.find('div', {'class': 'party'})
        name = card.find('div', {'class': 'name'})
        info = card.find('div', {'class': 'info'})

        last_segment_match = re.search(r"/+([^\W_]\w*)\W*$", url)
        sig_candidate_id = last_segment_match.group(
            1) if last_segment_match else ""

        extracted[url] = {'sig_candidate_id': sig_candidate_id,
                          'name': name.text.strip() if name else None,
                          'party': party.find('div', {'class': 'value'}).text if party else None,
                          'info': " ".join([e.text for e in info]) if info else None,
                          'score': score.find('div', {'class': 'value'}).text if score else None}
    return extracted


def extract_files(files: list, cards: bool = True):

    extracted = []

    for file in files:
        with open(file, 'r') as f:
            file_contents = f.read()

        if cards:
            # this gets the values (dictvalues=list) of the defaultdict(dict)
            extracted += extract_card(driver=None, file=file_contents).values()
        else:
            extracted.append(extract(driver=None, file=file_contents))

    return extracted


def save_html(driver: webdriver.Chrome, filepath=None):

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    last_segment_match = re.search(r"/+([^\W_]\w*)\W*$", driver.current_url)
    sig_candidate_id = last_segment_match.group(
        1) if last_segment_match else ""

    filepath = Path(filepath) / \
        'HTML_FILES' if filepath else Path('HTML_FILES')
    filepath.mkdir(exist_ok=True)

    timestamp = datetime.strftime(datetime.now(), '%Y-%m-%d-%H%M%S-%f')

    with open(HTML_FILES / f"Ratings_{sig_candidate_id}-{timestamp}.html", 'w') as f:
        f.write(str(soup))


def save_extract(extracted: dict[dict], filepath=None):

    filepath = Path(filepath) / \
        'EXTRACT_FILES' if filepath else Path('EXTRACT_FILES')
    filepath.mkdir(exist_ok=True)

    timestamp = datetime.strftime(datetime.now(), '%Y-%m-%d-%H%M%S-%f')

    df = pandas.DataFrame.from_dict(extracted, orient='index')
    df.to_csv(filepath / f"Ratings-Extract_{timestamp}.csv", index=False)


def main():

    chrome_service = Service('chromedriver')
    chrome_options = Options()
    chrome_options.add_argument('incognito')
    chrome_options.add_argument('headless')
    chrome_driver = webdriver.Chrome(
        service=chrome_service, options=chrome_options)

    chrome_driver.get(URL)

    # close overlay
    ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

    try:
        WebDriverWait(chrome_driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[@id='legislators-container']//div[@class='pure-g legislator-list']"))
        )

    except TimeoutException:
        print("Cannot find Legislator Container. Quitting...")
        chrome_driver.quit()
        exit()

    while True:
        try:
            pagination = chrome_driver.find_element(
                By.XPATH, "//div[@class='pagination pure-u-md-1 pure-u-lg-3-4']")
            pagination.click()

        except NoSuchElementException:
            break
        except ElementClickInterceptedException:
            pass

    extracted = {}

    card_records = extract_card(chrome_driver)

    for i, candidate_url in tqdm(enumerate(card_records), total=len(card_records)):
        # striping the '#' would prevent the session from redirecting itself
        card_info = card_records[candidate_url]['info']
        chrome_driver.get(urljoin(chrome_driver.current_url, candidate_url))

        extracted[i] = extract(chrome_driver, card_info=card_info)
        save_html(chrome_driver, filepath=EXPORT_DIR)

    save_extract(extracted, filepath=EXPORT_DIR)


if __name__ == '__main__':
    _, EXPORT_DIR, URL, *FILES = sys.argv

    EXPORT_DIR = Path(EXPORT_DIR)
    HTML_FILES = EXPORT_DIR / "HTML_FILES"
    EXTRACT_FILES = EXPORT_DIR / "EXTRACT_FILES"

    if FILES:
        if len(FILES) == 1:
            extract_files(FILES, cards=True)
        else:
            extract_files(FILES, cards=False)
    else:
        main()
