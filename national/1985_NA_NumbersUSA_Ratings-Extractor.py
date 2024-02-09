# This is the webscraping script for NumbersUSA, sig_id=1985

from urllib.parse import urlparse, urljoin
from datetime import datetime
from pathlib import Path

import pandas
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from tqdm import tqdm


URL = "https://grades.numbersusa.com/"


def extract(page_source):

    soup = BeautifulSoup(page_source, 'html.parser')
    info_container = soup.find('div', {'class': 'rep-info-container'})
    info_text = info_container.get_text(strip=True, separator=';')
    nav_container = soup.find('div', {'class': 'tab-nav-container'})
    score_containers = nav_container.find_all('a', {'class', 'nav-link'})

    def get_score(x): return x.get_text(strip=True).split(':')

    scores = {get_score(score)[0].strip(): get_score(score)[-1].strip() for score in score_containers}
    return {'info': info_text} | scores


def get_cpage_urls(page_source):
    soup = BeautifulSoup(page_source, 'html.parser')
    rows = soup.find_all('row', {'class': 'rep-link'})
    def clean(x): return x.lstrip('go(\')').rstrip('\');')
    return [urlparse(urljoin(URL, clean(row['onclick']))) for row in rows]


def save_html(page_source, filepath, *additional_info):

    soup = BeautifulSoup(page_source, 'html.parser')

    filepath = Path(filepath) / 'HTML_FILES'
    filepath.mkdir(exist_ok=True)

    timestamp = datetime.strftime(datetime.now(), '%Y-%m-%d-%H%M%S-%f')

    with open(filepath / f"Ratings_{'-'.join(map(str, additional_info))}"
                         f"{'-' if additional_info else ''}{timestamp}.html", 'w') as f:
        f.write(str(soup))


def save_extract(extracted: dict[dict], filepath, *additional_info):

    filepath = Path(filepath) / 'EXTRACT_FILES'
    filepath.mkdir(exist_ok=True)

    timestamp = datetime.strftime(datetime.now(), '%Y-%m-%d-%H%M%S-%f')

    df = pandas.DataFrame.from_records(extracted)
    df.to_csv(
        filepath / f"Ratings-Extract_{'-'.join(map(str, additional_info))}"
                   f"{'-' if additional_info else ''}{timestamp}.csv", index=False)


def main():
    chrome_service = Service('chromedriver')
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('incognito')
    chrome_options.add_argument('headless')

    chrome_driver = webdriver.Chrome(
        service=chrome_service, options=chrome_options)

    chrome_driver.get(URL)

    search_button = chrome_driver.find_element(
        By.XPATH, "//input[@value='Search']")
    search_button.click()

    cpage_urls = get_cpage_urls(chrome_driver.page_source)
    save_html(chrome_driver.page_source, EXPORT_DIR)

    extracted = []

    for url in tqdm(cpage_urls):
        chrome_driver.get(url.geturl())
        save_html(chrome_driver.page_source, EXPORT_DIR)
        extracted.append(extract(chrome_driver.page_source))

    save_extract(extracted, EXPORT_DIR)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(prog='sig_webscrape')
    parser.add_argument(
        'exportdir', help='file directory of where the files exports to')
    parser.add_argument('-f', '--htmldir', help='file directory of html files')

    args = parser.parse_args()

    EXPORT_DIR = Path(args.exportdir)
    main()
