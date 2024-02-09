
import sys
import pandas
import re

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import Select

from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path


URL = "https://texasrighttolife.com/legislative-scores/"
FILENAME = "_TX_RTL_Ratings"
TIMESTAMP = datetime.strftime(datetime.now(), '%Y-%m-%d')


def select_maximum(driver:webdriver.Chrome):

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    active_tab = soup.find('button', {'class':'tablinks active'})['onclick']
    active_tab_params = re.search(r'.*\((?P<param>.*)\)', active_tab)
    selected_office = active_tab_params.group('param').split(',')[1].strip(" '")
    
    select = Select(driver.find_element(By.XPATH, f"//div[@id=\'{selected_office}\']//select"))
    table_info = soup.find('div', {'id':f"{selected_office.rstrip('Tab')}_info"}).text
    max_entries = re.search(r'.*of\s(?P<num>\d+)\sentries',table_info).group('num')

    driver.execute_script(f"arguments[0].setAttribute('value', {max_entries})", select.options[-1])
    select.select_by_value(max_entries)


def extract(driver:webdriver.Chrome, file:str=None):

    if file:
        soup = BeautifulSoup(file, 'html.parser')
    
    else:
        soup = BeautifulSoup(driver.page_source, 'html.parser')

    active_tab = soup.find('button', {'class':'tablinks active'})['onclick']
    active_tab_params = re.search(r'.*\((?P<param>.*)\)', active_tab)
    selected_office = active_tab_params.group('param').split(',')[1].strip(" '")
    
    table = soup.find('div', {'id':selected_office}).table
    headers = [th.text.strip() for th in table.thead.find_all('th')]
    rows = [tr.find_all('td') for tr in table.tbody.find_all('tr')]

    extracted = []

    for row in rows:
        info = [row[0].text.strip(), 
                row[1].p.text.strip(),
                row[2].text.strip()]
        scores = [c.span.text.strip() for c in row[3:]]
        extracted.append(dict(zip(headers, info+scores)))

    return extracted


def download_page(driver:webdriver.Chrome):

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    active_tab = soup.find('button', {'class':'tablinks active'})['onclick']
    active_tab_params = re.search(r'.*\((?P<param>.*)\)', active_tab)
    selected_office = active_tab_params.group('param').split(',')[1].strip(" '")

    HTML_FILES.mkdir(exist_ok=True)

    with open(HTML_FILES / f"{FILENAME}_{selected_office.rstrip('Tab')}-{TIMESTAMP}.html", 'w') as f:
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

    tab_buttons = chrome_driver.find_elements(By.XPATH, "//button[@class='tablinks']")

    extracted = []

    for tab_button in tab_buttons[:-1]:
        tab_button.click()
        select_maximum(chrome_driver)
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
