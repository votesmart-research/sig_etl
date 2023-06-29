
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


URL = "https://scorecard.progressivemass.com/all-legislators/"
FILENAME = "_MA_ProgressiveMA_Ratings"
TIMESTAMP = datetime.strftime(datetime.now(), '%Y-%m-%d')


def extract(driver:webdriver.Chrome, file:str=None):

    if file:
        soup = BeautifulSoup(file, 'html.parser')
    
    else:
        soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    selected_tab = soup.find('div', {'class':'RRT__tab', 'aria-selected':'true'})

    table = soup.find('table')
    headers = [th.text for th in table.thead.find_all('th')]
    rows = [tr.find_all('td') for tr in table.tbody.find_all('tr')]
    
    get_text = lambda x: x.text.strip().replace('\xa0', '')

    return [dict(zip(headers, map(get_text, row))) | {'office':selected_tab.text} for row in rows]


def download_page(driver:webdriver.Chrome):

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    selected_tab = soup.find('div', {'class':'RRT__tab', 'aria-selected':'true'})
    office = selected_tab.text

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
    chrome_options.add_argument('headless')
    chrome_driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    chrome_driver.get(URL)

    # close overlay
    ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

    tabs = chrome_driver.find_elements(By.XPATH, "//div[@role='tab']")

    extracted = []

    for tab in tabs:
        tab.click()
        extracted += extract(chrome_driver)
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
