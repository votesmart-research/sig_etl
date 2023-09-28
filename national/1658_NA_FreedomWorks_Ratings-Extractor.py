
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


FILENAME = "_NA_FreedomWorks_Ratings"
TIMESTAMP = datetime.strftime(datetime.now(), '%Y-%m-%d')


def extract(driver:webdriver.Chrome, file:str=None):

    if file:
        soup = BeautifulSoup(file, 'html.parser')
    
    else:
        soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    table = soup.find('table', {'class':'vote-table'})
    articles = table.find_all('article', {'class':'legislator-score-card'})

    def _extract_article(article:BeautifulSoup):
        sig_candidate_id = article['id']
        candidate_name = article.find('p', {'class':'card-name'}).text
        card_info = article.find_all('span', {'class':'meta-item'})
        office = card_info[0].text
        district = card_info[-1].text
        scores = article.find_all('li', {'class':'card-score'})

        return {'sig_candidate_id': sig_candidate_id,
                'candidate_name': candidate_name,
                'office': office,
                'district': district} | \
                {score.span.text: score.strong.text.strip() for score in scores}
    
    extracted = [_extract_article(article) for article in articles]
    return extracted


def download_page(driver:webdriver.Chrome):
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    office = driver.current_url.rstrip('/').split('/')[-1]

    HTML_FILES.mkdir(exist_ok=True)

    with open(HTML_FILES / f"{FILENAME}_{office}-{TIMESTAMP}.html", 'w') as f:
        f.write(soup.prettify())


def extract_from_file(files:list):

    extracted  = []

    for file in files:

        with open(file, 'r') as f:
            file_contents = f.read()
        
        extracted += extract(driver=None, file=file_contents)
    
    EXTRACT_FILES.mkdir(exist_ok=True)

    df = pandas.DataFrame.from_records(extracted)
    df.to_csv(EXTRACT_FILES / f"{FILENAME}-Extract_{TIMESTAMP}.csv", index=False)


def main():
    
    chrome_service = Service('chromedriver')
    chrome_options = Options()
    chrome_options.add_argument('incognito')
    # chrome_options.add_argument('headless')
    chrome_driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    chrome_driver.get(URL)

    # close overlay
    ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()
    office = chrome_driver.current_url.rstrip('/').split('/')[-1]

    extracted = extract(chrome_driver)
    download_page(chrome_driver)

    EXTRACT_FILES.mkdir(exist_ok=True)

    df = pandas.DataFrame.from_records(extracted)
    df.to_csv(EXTRACT_FILES / f"{FILENAME}-Extract_{office}-{TIMESTAMP}.csv", index=False)
    

if __name__ == '__main__':
    _, EXPORT_DIR, URL, *FILES = sys.argv

    EXPORT_DIR = Path(EXPORT_DIR)
    HTML_FILES = EXPORT_DIR / "HTML_FILES"
    EXTRACT_FILES = EXPORT_DIR / "EXTRACT_FILES"

    if FILES:
        extract_from_file(FILES)
    else:
        main()
