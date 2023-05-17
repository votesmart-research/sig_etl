
import sys
import pandas
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path


URL = "https://public.tableau.com/views/Scorecard_16504963434600/Story1?:showVizHome=no"
FILENAME = "_WA_WCV_Ratings"
TIMESTAMP = datetime.strftime(datetime.now(), '%Y-%m-%d')


def extract(driver:webdriver.Chrome, file:str=None):

    if file:
        soup = BeautifulSoup(file, 'html.parser')
    
    else:
        soup = BeautifulSoup(driver.page_source, 'html.parser')

    header_div = soup.find('div', {'class':'tab-vizLeftSceneMargin-focusbox'})
    header_raw = header_div['aria-label'].split(',') if header_div else None
    slice_to = -1

    for i in range(0, len(header_raw)):
        if header_raw[i] == ' ':
            slice_to = i
    
    headers = list(map(lambda x: x.strip(), header_raw[0:slice_to]))
    columns = soup.find_all('div', {'class':'tab-vizHeaderHolderWrapper'})

    rows = []
    for column in columns:
        values = column.find_all('div', {'class':'tab-vizHeader'})
        rows.append(list(map(lambda x: x.text.strip(), values)))

    extracted = dict(zip(headers, rows))

    return extracted


def download_page(driver:webdriver.Chrome, office=None):

    soup = BeautifulSoup(driver.page_source, 'html.parser')

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

    df = pandas.DataFrame.from_dict(extracted)
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

    try:
        WebDriverWait(chrome_driver,10).until(
            EC.presence_of_element_located((By.XPATH, "//div[@id='main-content']//div[@id='tab-dashboard-region']"))
        )
        
    except TimeoutException:
        print("Cannot find main dashboard. Quitting...")
        chrome_driver.quit()
        exit()

    offices = chrome_driver.find_elements(By.XPATH, "//div[@class='tabStoryPointContent tab-widget']")
    extracted = {}

    for i in range(0, len(offices)):
        
        offices[i].click()
        offices = chrome_driver.find_elements(By.XPATH, "//div[@class='tabStoryPointContent tab-widget']")

        office_name = offices[i].text
        _extracted = extract(chrome_driver)
        
        if extracted:
            while list(extracted.values())[-1] == _extracted:
                time.sleep(1)
                _extracted = extract(chrome_driver)

        extracted[office_name] = _extracted
        download_page(chrome_driver, office=office_name)

    EXTRACT_FILES.mkdir(exist_ok=True)

    for office, records in extracted.items():
        df = pandas.DataFrame.from_dict(records)
        df.to_csv(EXTRACT_FILES / f"{FILENAME}-Extract_{office}-{TIMESTAMP}.csv", index=False)
    

if __name__ == '__main__':
    _, EXPORT_DIR, *FILES = sys.argv

    EXPORT_DIR = Path(EXPORT_DIR)
    HTML_FILES = EXPORT_DIR / "HTML_FILES"
    EXTRACT_FILES = EXPORT_DIR / "EXTRACT_FILES"

    if FILES:
        extract_from_file(FILES)
    else:
        main()
