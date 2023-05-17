# This is the webscraping script for Libertas Institute, sig_id=2414

import sys
import pandas

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from tqdm import tqdm


FILENAME = "_UT_Libertas_Ratings"
DOMAIN_URL = "https://libertas.org"
TIMESTAMP = datetime.strftime(datetime.now(), '%Y-%m-%d')

def candidate_extract(driver:webdriver.Chrome, file:str=None):
    if file:
        soup = BeautifulSoup(file, 'html.parser')
    
    else:
        soup = BeautifulSoup(driver.page_source, 'html.parser')

    ratings_table = soup.find('table')
    legislator_info = ratings_table.find_previous_siblings('div')[1]
    sig_candidate_id = driver.current_url.strip('/').split('/')[-1]

    d = {}
    for item in legislator_info.text.split():
        if ':' in item:
            d[item.strip(':')] = ''
        else:
            if(d):
                if not d[list(d).pop()]:
                    d[list(d).pop()]+=item
                else:
                    d[list(d).pop()]+=f" {item}"

    headers = [th.text for th in ratings_table.thead.find_all('th')]
    row = ratings_table.tbody.tr.find_all('td')
    ratings_d = dict(zip(headers, map(lambda x: x.text.strip(), row)))

    return {'sig_candidate_id':sig_candidate_id} | d | ratings_d 


def table_extract(driver:webdriver.Chrome, file:str=None):

    def _extract_table(table, **columns):

        headers = []
        for th in table.thead.find_all('th'):
            if th.span:
                th.span.decompose()
            headers.append(th.text)
        
        headers.append('url')

        get_text = lambda x: x.text.strip()
        
        rows = []
        for tr in table.tbody.find_all('tr'):
            tds = list(map(get_text, tr.find_all('td')))
            url = tr.find('a')['href']
            tds.append(url)
            rows.append(tds)

        return [dict(zip(headers, row)) | columns for row in rows]

    if file:
        soup = BeautifulSoup(file, 'html.parser')
    
    else:
        soup = BeautifulSoup(driver.page_source, 'html.parser')

    table_house = soup.find('table', {'id': 'index_house'})
    table_senate = soup.find('table', {'id': 'index_senate'})

    return _extract_table(table_house, office='house') + _extract_table(table_senate, office='senate')


def download_page(driver:webdriver.Chrome):

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    sig_candidate_id = driver.current_url.strip('/').split('/')[-1]
    HTML_FILES.mkdir(exist_ok=True)

    with open(HTML_FILES / f"{FILENAME}_{sig_candidate_id}_{TIMESTAMP}.html", 'w') as f:
        f.write(soup.prettify())


def extract_from_file(files:list):

    extracted  = []

    for file in files:

        with open(file, 'r') as f:
            file_contents = f.read()
        
        extracted += candidate_extract(driver=None, file=file_contents)
    
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

    candidates = table_extract(chrome_driver)
    extracted = []

    for candidate in tqdm(candidates):
        chrome_driver.get(DOMAIN_URL + candidate['url'])
        extracted.append(candidate_extract(chrome_driver))
        download_page(chrome_driver)

    EXTRACT_FILES.mkdir(exist_ok=True)

    df = pandas.DataFrame.from_records(extracted)
    df.to_csv(EXTRACT_FILES / f"{FILENAME}-Extract_{TIMESTAMP}.csv", index=False)
    

if __name__ == '__main__':
    _, EXPORT_DIR, URL, *FILES = sys.argv

    EXPORT_DIR = Path(EXPORT_DIR)
    HTML_FILES = EXPORT_DIR / "HTML_FILES"
    EXTRACT_FILES = EXPORT_DIR / "EXTRACT_FILES"

    if FILES:
        extract_from_file(FILES)
    else:
        main()
