
import sys
import re
from datetime import datetime
from pathlib import Path


import pandas
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains
from tqdm import tqdm


URL = "https://civitasaction.org/rankings/"
FILENAME = "_NC_Civitas_Ratings"
TIMESTAMP = datetime.strftime(datetime.now(), '%Y-%m-%d')


def get_candidate_links(driver:webdriver.Chrome):
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    tables = soup.find_all('table')
    links = []

    for table in tables:
        rows = table.find_all('tr')[1:]
        links += [row.a['href'] for row in rows]

    return links


def extract(driver:webdriver.Chrome, file:str=None):

    if file:
        soup = BeautifulSoup(file, 'html.parser')
    else:
        soup = BeautifulSoup(driver.page_source, 'html.parser')

    clean_url = re.sub(r'\?(.*)', '', driver.current_url) if driver else None
    sig_candidate_id = clean_url.strip('/').split('/')[-1] if clean_url else None
    score_wrapper = soup.find('div', {'class':'personIntro'})
    info = soup.find('div', {'class':'personDetails'})
    info_split = [i for i in map(lambda x: x.strip(), info.find('p').text.split('\n')) if i]

    all_scores = score_wrapper.find_all('div', {'class':'score'})
    current_score = all_scores[0]
    lifetime_score = all_scores[-1]

    current_score_title = current_score.find('div',{'class':'title'}).text.strip()
    current_score_value = current_score.find('div',{'class':'value hiddenBig'}).em.text.strip()

    lifetime_score_title = lifetime_score.find('div',{'class':'title'}).text.strip()
    lifetime_score_value = lifetime_score.find('div',{'class':'value'}).em.text.strip()

    name = info_split[0]
    district = info_split[1]

    return {'sig_candidate_id': sig_candidate_id,
            'candidate_name': name,
            'district': district,
            current_score_title: current_score_value,
            lifetime_score_title: lifetime_score_value}


def download_page(driver:webdriver.Chrome):

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    clean_url = re.sub(r'\?(.*)', '', driver.current_url) if driver else None
    sig_candidate_id = clean_url.strip('/').split('/')[-1] if clean_url else None

    HTML_FILES.mkdir(exist_ok=True)

    with open(HTML_FILES / f"{FILENAME}_{sig_candidate_id}-{TIMESTAMP}.html", 'w') as f:
        f.write(soup.prettify())


def extract_from_file(files:list):

    extracted  = []

    for file in files:
        sig_candidate_id = "-".join(str(file).split('_')[-1].split('-')[:-3])

        with open(file, 'r') as f:
            file_contents = f.read()
        
        extracted.append(extract(driver=None, file=file_contents) |
                         {'sig_candidate_id': sig_candidate_id})
    
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

    year_selector = Select(chrome_driver.find_element(By.XPATH, "//nav[@class='filters toggler']/select"))
    year_selector.select_by_value(YEAR)

    candidate_links = get_candidate_links(chrome_driver)

    extracted = []

    for link in tqdm(candidate_links, desc='Extracting...'):
        chrome_driver.get(link)
        extracted.append(extract(chrome_driver))
        download_page(chrome_driver)

    EXTRACT_FILES.mkdir(exist_ok=True)

    df = pandas.DataFrame.from_records(extracted)
    df.to_csv(EXTRACT_FILES / f"{FILENAME}-Extract_{TIMESTAMP}.csv", index=False)
    

if __name__ == '__main__':
    _, EXPORT_DIR, YEAR, *FILES = sys.argv

    EXPORT_DIR = Path(EXPORT_DIR)
    HTML_FILES = EXPORT_DIR / "HTML_FILES"
    EXTRACT_FILES = EXPORT_DIR / "EXTRACT_FILES"

    if FILES:
        extract_from_file(FILES)
    else:
        main()
