
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


URL = "https://massfiscalscorecard.org/"
FILENAME = "_MA_MassFiscal_Ratings"
TIMESTAMP = datetime.strftime(datetime.now(), '%Y-%m-%d')


def extract(driver:webdriver.Chrome, file:str=None):

    if file:
        soup = BeautifulSoup(file, 'html.parser')
    
    else:
        soup = BeautifulSoup(driver.page_source, 'html.parser')

    header_table = soup.find('table', {'class': 'hidden-xs'})
    table = soup.find('table', {'class': 'legislators-table'})

    headers = [th.text.strip() for th in header_table.thead.find_all('th')]

    extracted = []
    get_text = lambda x: x.text.strip() if x.text else x.text

    for tr in table.tbody.find_all('tr'):
        columns = tr.find_all('td')
        sig_candidate_id = columns[0].a['href'].split('=')[-1]
        party = columns[1].img['src'].split('/')[-1].replace('-Icon.png','')

        record = dict(zip(headers, map(get_text, columns)))
        record.update({headers[1]:party})
        extracted.append({'sig_candidate_id': sig_candidate_id} |
                         record )

    return extracted


def select_by_year(driver:webdriver.Chrome, year):

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    session_list = soup.find('ul', {'class':'session-datapoint-dropdown'})
    session_texts = [a.text for a in session_list.find_all('a')]

    for text in session_texts:

        driver.find_element(By.ID, 'legislators-session-dropdown-btn').click()
        dropdown_menu = driver.find_element(By.XPATH, "//ul[@class='dropdown-menu session-datapoint-dropdown']")
        session_links = dropdown_menu.find_elements(By.TAG_NAME, 'a')

        for link in session_links:
            if link.text == text:
                link.click()
                span = BeautifulSoup(driver.page_source, 'html.parser').find('span', {'id':'session-year-span'})
                if str(year) in span.text:
                    return span.text.strip(':')
    

def download_page(driver:webdriver.Chrome):

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    HTML_FILES.mkdir(exist_ok=True)

    with open(HTML_FILES / f"{FILENAME}_{TIMESTAMP}.html", 'w') as f:
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

    span_selected = select_by_year(chrome_driver, YEAR)
    print(f"Extracting from {span_selected}...")

    extracted = extract(chrome_driver)
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
