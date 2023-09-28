
import sys
import pandas

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path



def go_and_get_soup(url):

    chrome_service = Service('chromedriver')
    chrome_options = Options()
    chrome_options.add_argument('incognito')
    chrome_options.add_argument('headless')
    driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    driver.get(url)
    soup = get_soup(driver)

    if not driver:
        driver.quit()
    
    return soup


def get_soup(driver, filepath=None):

    if driver:
        return BeautifulSoup(driver.page_source, 'html.parser')
    
    elif filepath:
        with open(filepath, 'r') as f:
            return BeautifulSoup(f.read(), 'html.parser')

    else:
        return BeautifulSoup("")


def extract(soup):

    table = soup.find('table')
    headers = [th.text for th in table.thead.find_all('th')]
    rows = [tr.find_all('td') for tr in table.tbody.find_all('tr')]

    get_text = lambda x: x.text.strip()

    return [dict(zip(headers, map(get_text, row))) for row in rows]   


def extract_from_file(files:list):

    extracted  = []

    for file in files:

        with open(file, 'r') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
        
        extracted += extract(soup)
    
    save_extract(extracted)


def save_html(soup, *additional_info):

    HTML_FILES = EXPORT_DIR / "HTML_FILES"
    HTML_FILES.mkdir(exist_ok=True)

    timestamp = datetime.strftime(datetime.now(), '%Y-%m-%d-%H%M%S-%f')

    with open(HTML_FILES / f"Ratings_{'-'.join(map(str, additional_info))}-{timestamp}.html", 'w') as f:
        f.write(soup.prettify())


def save_extract(extracted:dict[list], *additional_info):

    EXTRACT_FILES = EXPORT_DIR / "EXTRACT_FILES"
    EXTRACT_FILES.mkdir(exist_ok=True)
    timestamp = datetime.strftime(datetime.now(), '%Y-%m-%d-%H%M%S-%f')

    df = pandas.DataFrame.from_records(extracted)
    df.to_csv(EXTRACT_FILES / f"Ratings-Extract_{'-'.join(map(str, additional_info))}-{timestamp}.csv", index=False)


def main():

    chrome_service = Service('chromedriver')
    chrome_options = Options()
    chrome_options.add_argument('incognito')
    chrome_options.add_argument('headless')
    chrome_driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    chrome_driver.get(URL)

    extracted = []

    while True:
        try:
            next_button = chrome_driver.find_element(By.XPATH, "//a[@class='paginate_button next']")
        except NoSuchElementException:
            next_button = None

        extracted += extract(get_soup(chrome_driver))
        save_html(get_soup(chrome_driver))

        if next_button:
            next_button.click()
        else:
            break

    save_extract(extracted)


if __name__ == '__main__':
    _, EXPORT_DIR, URL, *FILES = sys.argv

    EXPORT_DIR = Path(EXPORT_DIR)
    HTML_FILES = EXPORT_DIR / "HTML_FILES"
    EXTRACT_FILES = EXPORT_DIR / "EXTRACT_FILES"

    if FILES:
        extract_from_file(FILES)
    else:
        main()
