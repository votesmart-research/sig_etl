
import sys
import pandas
import re

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
from tqdm import tqdm


FILENAME = "_MN_ProChoice_Ratings"
TIMESTAMP = datetime.strftime(datetime.now(), '%Y-%m-%d')


def get_candidate_urls(driver:webdriver.Chrome):

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    office_sections = soup.find_all('div', {'class':'list-item-content'})
    candidate_urls = []

    for section in office_sections:
        candidate_urls += [a['href'].lstrip('/') for a in section.find_all('a')]

    return candidate_urls


def extract(driver:webdriver.Chrome, file:str=None):

    if file:
        soup = BeautifulSoup(file, 'html.parser')
    
    else:
        soup = BeautifulSoup(driver.page_source, 'html.parser')

    rating_regex = re.compile(r'(?P<label>Grade):\s?(?P<rating>.*)')

    try:
        WebDriverWait(driver,10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@class='sqs-block-content']"))
            )
    except TimeoutException:
        last_segment_match = re.search(r"[^/]+$", driver.current_url)
        url_segment = last_segment_match.group() if last_segment_match else ""

        return {'candidate_info': None,
                'rating': None,
                'url_segment': url_segment}

    block_content = soup.find('div', {'class':'sqs-block-content'})
    candidate_info = block_content.find('h4')
    rating_info = rating_regex.search(block_content.find(string=rating_regex))

    return {'candidate_info': candidate_info.text if candidate_info else None,
            rating_info.group('label') if rating_info else 'rating': 
                rating_info.group('rating') if rating_info else None}


def download_page(driver:webdriver.Chrome):

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    last_segment_match = re.search(r"[^/]+$", driver.current_url)
    url_segment = last_segment_match.group() if last_segment_match else ""

    HTML_FILES.mkdir(exist_ok=True)

    with open(HTML_FILES / f"{FILENAME}_{url_segment}-{TIMESTAMP}.html", 'w') as f:
        f.write(soup.prettify())


def extract_from_file(files:list):

    extracted  = []

    for file in files:

        with open(file, 'r') as f:
            file_contents = f.read()
        
        extracted.append(extract(driver=None, file=file_contents))
    
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

    url_domain = re.match(r'^(?:https?:\/\/)?(?:www\.)?([^\/]+)', chrome_driver.current_url).group(0)

    candidate_urls = get_candidate_urls(chrome_driver)
    extracted = []

    for url in tqdm(candidate_urls):
        chrome_driver.get(f'{url_domain}/{url}')
        extracted.append(extract(chrome_driver))
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
