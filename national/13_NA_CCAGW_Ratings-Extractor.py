
import sys
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


MAIN_URL = "https://www.ccagwratings.org"
URL = "https://www.ccagwratings.org/legislators"
FILENAME = "_NA_CCAGW_Ratings"
TIMESTAMP = datetime.strftime(datetime.now(), '%Y-%m-%d')


def extract(driver:webdriver.Chrome, file:str=None):

    if file:
        soup = BeautifulSoup(file, 'html.parser')
    
    else:
        soup = BeautifulSoup(driver.page_source, 'html.parser')

    table = soup.find('table')

    headers = [th.text.strip() for th in table.thead.find_all('th')]

    extracted = {}

    for tr in table.tbody.find_all('tr'):
        candidate_url = tr.find('a')['href']
        sig_candidate_id = candidate_url.split('/')[-1]
        column_texts = [td.text.strip() for td in tr.find_all('td')]

        extracted[candidate_url] = dict(zip(headers, column_texts)) | \
                                   {'sig_candidate_id': sig_candidate_id}

    return extracted


def extract_candidate(driver:webdriver.Chrome, file:str=None):

    if file:
        soup = BeautifulSoup(file, 'html.parser')
        
    else:
        soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    ratings = soup.find('div', {'class':'ratings'})
    rating_texts = [li.text.split(':') for li in ratings.find_all('li')]
    ratings_dict = {rt[0]: rt[-1].strip() for rt in rating_texts}

    return ratings_dict


def pager_urls(driver:webdriver.Chrome):

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    pager = soup.find('ul', {'class':'pager'})

    first_page = pager.find('li', {'class':'first'}).text
    last_page = pager.find('li', {'class':'last'}).a['href'].split('=')[-1]

    urls = [f"{URL}?page={i}" for i in range(int(first_page)-1, int(last_page))]

    return urls


def download_page(driver:webdriver.Chrome):

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    if len(driver.current_url.split('?')) > 1:
        factor = driver.current_url.split('?')[-1]
    else:
        factor = driver.current_url.split('/')[-1]

    HTML_FILES.mkdir(exist_ok=True)

    with open(HTML_FILES / f"{FILENAME}_{factor}-{TIMESTAMP}.html", 'w') as f:
        f.write(soup.prettify())


def extract_from_file(files:list):

    _extracted = {}

    for p_file in filter(lambda x: 'page' in x, files):    
        with open(p_file, 'r') as f:
            p_file_contents = f.read()
        
        _extracted |= extract(driver=None, file=p_file_contents)

    files_dict = {f.split('_')[-1].split('-')[0]: f for f in filter(lambda x: 'page' not in x, files)}
    extracted  = []
    
    for info in _extracted.values():
        sig_candidate_id = info['sig_candidate_id']

        with open(files_dict[sig_candidate_id], 'r') as f:
            file_contents = f.read()
        
        extracted.append(info | extract_candidate(driver=None, file=file_contents))
    
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

    _extracted = {}

    for url in tqdm(pager_urls(chrome_driver), desc="Iterating pages..."):
        chrome_driver.get(url)
        _extracted |= extract(chrome_driver)
        download_page(chrome_driver)
    
    extracted = []

    for candidate_url, info in tqdm(_extracted.items(), desc="Extracting ratings..."):
        chrome_driver.get(f"{MAIN_URL}{candidate_url}")
        extracted.append(info | extract_candidate(chrome_driver))
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
        extract_from_file(FILES)
    else:
        main()
