
import sys
import pandas

from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from bs4 import BeautifulSoup
from tqdm import tqdm


URL = "http://gachamberscore.com/legislators/"
FILENAME = "_GA_COC_Ratings"
TIMESTAMP = datetime.strftime(datetime.now(), '%Y-%m-%d')
RATINGS = {'yesPos': '+', 
           'noPos': '-', 
           'legPosCell': '*', 
           'presPos': '*'}


def extract(driver:webdriver.Chrome, file:str=None):

    if file:
        soup = BeautifulSoup(file, 'html.parser')
    
    else:
        soup = BeautifulSoup(driver.page_source, 'html.parser')

    tables = soup.find_all('table', {'class':'resultsTable legListTable'})
    get_text = lambda x: x.text.strip()

    def _extract(table):
        office = table.parent.find('h2').text.strip()
        headers = ['sig_candidate_id'] + [th.text.strip() for th in table.thead.find_all('th')]
        rows = []
        for tr in table.tbody.find_all('tr'):
            sig_candidate_id = tr['data-link'].strip('/').split('/')[-1]
            columns = list(map(get_text, tr.find_all('td')))
            rows.append([sig_candidate_id] + columns)

        return [dict(zip(headers, row)) | {'office': office} for row in rows]
    
    extracted = []

    for table in tables:
        extracted += _extract(table)
    return extracted


def extract_candidate(driver:webdriver.Chrome, file:str=None):

    if file:
        soup = BeautifulSoup(file, 'html.parser')
    
    else:
        soup = BeautifulSoup(driver.page_source, 'html.parser')

    def _extract_ratings(soup):
        table = soup.find('table', {'class':'resultsTable legVoteTable'})
        positions = table.find_all('td', {'class': 'legPosCell'}) if table else []
        return "".join([str(RATINGS.get(p.attrs['class'][-1]))for p in positions])
    
    return {'sig_rating': _extract_ratings(soup)}
    

def extract_from_file(files:list[Path]):

    extracted  = []
    sort_by_mtime = sorted([(file.stat().st_mtime, file) for file in files])

    first_file = sort_by_mtime[0][1]

    with open(first_file, 'r') as f:
        extracted_table = extract(driver=None, file=f.read())

    for e, file in zip(extracted_table, sort_by_mtime[1:]):
        with open(file[1], 'r') as f:
            extracted.append(e | extract_candidate(driver=None, file=f.read()))

    EXTRACT_FILES.mkdir(exist_ok=True)

    df = pandas.DataFrame.from_records(extracted)
    df.to_csv(EXTRACT_FILES / f"{FILENAME}-Extract_{TIMESTAMP}.csv", index=False)


def download_page(driver:webdriver.Chrome):

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    HTML_FILES.mkdir(exist_ok=True)

    with open(HTML_FILES / f"{FILENAME}_{TIMESTAMP}.html", 'w') as f:
        f.write(soup.prettify())


def download_candidate_page(driver:webdriver.Chrome):

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    sig_candidate_id = driver.current_url.strip('/').split('/')[-1]

    HTML_FILES.mkdir(exist_ok=True)

    with open(HTML_FILES / f"{FILENAME}_{sig_candidate_id}-{TIMESTAMP}.html", 'w') as f:
        f.write(soup.prettify())


def main():
    
    chrome_service = Service('chromedriver')
    chrome_options = Options()
    chrome_options.add_argument('incognito')
    chrome_options.add_argument('headless')
    chrome_driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    chrome_driver.get(URL)

    # close overlay
    ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

    extracted_table = extract(chrome_driver)
    download_page(chrome_driver)

    extracted = []
    
    for et in tqdm(extracted_table):
        chrome_driver.get(URL + et['sig_candidate_id'])
        extracted.append(et | extract_candidate(chrome_driver))
        download_candidate_page(chrome_driver)

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
