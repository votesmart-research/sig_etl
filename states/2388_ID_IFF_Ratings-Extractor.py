
import sys
import re

import pandas

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from tqdm import tqdm


URL = "https://index.idahofreedom.org/scorecard-leaderboard/"
FILENAME = "_ID_IFF_Ratings"
TIMESTAMP = datetime.strftime(datetime.now(), '%Y-%m-%d')


def extract(driver:webdriver.Chrome, file:str=None):

    d = {}
    if file:
        soup = BeautifulSoup(file, 'html.parser')
    
    else:
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        d['sig_candidate_id'] = re.search(r'(?<=id\=)\w+',driver.current_url).group()
    
    current_scores = soup.find_all('div', {'class':'profile-score--score'})
    
    for current_score in current_scores:
        container = current_score.parent
        score_type = container.find('h3', {'class':'ct-headline'}).text.strip()
        lifetime_score = container.find('span', {'class':'lifetime-score'}).text.strip()
        d[score_type] = current_score.text.strip()
        d[f'{score_type} (lifetime)'] = lifetime_score
    
    return d


def extract_cards(driver:webdriver.Chrome, file:str=None):

    if file:
        soup = BeautifulSoup(file, 'html.parser')
    
    else:
        soup = BeautifulSoup(driver.page_source, 'html.parser')

    cards = soup.find_all('div', {'class':'bt-legislator-summary'})

    records = []

    for card in cards:
        d = {}
        image = card.find('div', {'class':'bt-legislator-image'})
        details = card.find('div', {'class': 'bt-legislator-details'})
        party = image.find('div', {'class':'bt-party'})
        d['candidate_url'] = image.a['href']
        for div in details.find_all('div')[:-1]:
            column = div['class'].pop().lstrip('bt-legislator-')
            value = div.text.strip()
            d[column] = value
        
        d['party'] = party.text.strip() if party else None
        records.append(d)

    return records


def download_page(driver:webdriver.Chrome):

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    sig_candidate_id = re.search(r'(?<=id\=)\w+',driver.current_url)

    HTML_FILES.mkdir(exist_ok=True)

    if sig_candidate_id:
        html_filename = f"{FILENAME}_{sig_candidate_id.group()}_{TIMESTAMP}.html"
    else:
        html_filename = f"{FILENAME}_{TIMESTAMP}.html"

    with open(HTML_FILES / html_filename, 'w') as f:
        f.write(soup.prettify())


def extract_from_file(files:list[Path]):

    extracted  = []
    sort_by_mtime = sorted([(file.stat().st_mtime, file) for file in files])

    first_file = sort_by_mtime[0][1]

    with open(first_file, 'r') as f:
        extracted_cards = extract_cards(driver=None, file=f.read())

    for e, file in zip(extracted_cards, sort_by_mtime[1:]):
        with open(file[1], 'r') as f:
            candidate_url = e.pop('candidate_url')
            sig_candidate_id = re.search(r'(?<=id\=)\w+', candidate_url).group()
            extracted.append({'sig_candidate_id': sig_candidate_id} |
                              e | extract(driver=None, file=f.read()))

    EXTRACT_FILES.mkdir(exist_ok=True)

    df = pandas.DataFrame.from_records(extracted)
    df.to_csv(EXTRACT_FILES / f"{FILENAME}-Extract_{TIMESTAMP}.csv", index=False)


def main():
    
    chrome_service = Service('chromedriver')
    chrome_options = Options()
    chrome_options.add_argument('incognito')
    chrome_options.add_argument('headless')
    chrome_driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    chrome_driver.get(URL)

    # close overlay
    ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

    extracted = []
    download_page(chrome_driver)
    records = extract_cards(chrome_driver)
    
    for record in tqdm(records):
        chrome_driver.get(record['candidate_url'])
        record.pop('candidate_url')
        extracted.append(extract(chrome_driver) | record)
        download_page(chrome_driver)

    EXTRACT_FILES.mkdir(exist_ok=True)

    df = pandas.DataFrame.from_records(extracted)
    df.to_csv(EXTRACT_FILES / f"{FILENAME}-Extract_{TIMESTAMP}.csv", index=False)
    

if __name__ == '__main__':
    _, EXPORT_DIR, *FILES = sys.argv

    EXPORT_DIR = Path(EXPORT_DIR)
    HTML_FILES = EXPORT_DIR / "HTML_FILES"
    EXTRACT_FILES = EXPORT_DIR / "EXTRACT_FILES"

    if FILES:
        files_path = [Path(file) for file in FILES]
        extract_from_file(files_path)
    else:
        main()
