# This is a webscraping script for groups who uses Voter Voice.

import sys
import pandas

from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from bs4 import BeautifulSoup, Tag as BSoupTag
from pathlib import Path
from datetime import datetime


RATINGS_METHODOLOGY = {'Voted with us': '+',
                       'Voted against us': '-',
                       'No position': '*',
                       None: ''}


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


def get_soup(driver: RemoteWebDriver, filepath=None):

    if driver:
        return BeautifulSoup(driver.page_source, 'html.parser')

    elif filepath:
        with open(filepath, 'r') as f:
            return BeautifulSoup(f.read(), 'html.parser')

    else:
        return BeautifulSoup("")


def extract(soup: BSoupTag):

    office = soup.find(
        'div', {'class': 'vv-tab-menu-item-active'}).text.strip()
    sessions = soup.find_all('section', {'class': 'vv-scorecard-section'})

    def _extract_row(row):
        columns = row.find_all('td')
        rating_string = [td.span['title']
                         if td.span else None for td in columns[2:]]
        translated_rating_string = "".join(
            [RATINGS_METHODOLOGY.get(c) for c in rating_string])

        return {'info': columns[0]['title'],
                'sig_rating': columns[1].text,
                'sig_rating_string': translated_rating_string,
                'office': office}

    for session in sessions:
        span = session.header.text.strip()
        rows = session.table.tbody.find_all('tr')
        yield span, {i: _extract_row(row) for i, row in enumerate(rows)}


def extract_from_file(files: list):

    for file in files:

        with open(file, 'r') as f:
            file_contents = f.read()

        for session, records in extract(driver=None, file=file_contents):
            save_extract(records, session)


def save_html(soup: BSoupTag):

    HTML_FILES = EXPORT_DIR / "HTML_FILES"
    HTML_FILES.mkdir(exist_ok=True)

    office = soup.find(
        'div', {'class': 'vv-tab-menu-item-active'}).text.strip()
    timestamp = datetime.strftime(datetime.now(), '%Y-%m-%d-%H%M%S-%f')

    with open(HTML_FILES / f"Ratings_{office}-{timestamp}.html", 'w') as f:
        f.write(soup.prettify())


def save_extract(extracted: dict[dict], *additional_info):

    EXTRACT_FILES = EXPORT_DIR / "EXTRACT_FILES"
    EXTRACT_FILES.mkdir(exist_ok=True)

    timestamp = datetime.strftime(datetime.now(), '%Y-%m-%d-%H%M%S-%f')

    df = pandas.DataFrame.from_dict(extracted, orient='index')
    df.to_csv(EXTRACT_FILES /
              f"Ratings-Extract_{'-'.join(map(str, additional_info))}-{timestamp}.csv", index=False)


def main():

    chrome_service = Service('chromedriver')
    chrome_options = Options()
    chrome_options.add_argument('incognito')
    chrome_options.add_argument('headless')
    chrome_driver = webdriver.Chrome(
        service=chrome_service, options=chrome_options)

    chrome_driver.get(URL)

    try:
        WebDriverWait(chrome_driver, 10).until(
            EC.visibility_of_all_elements_located(
                (By.XPATH, '//table[@class="vvScorecardAggregate"]/tbody/tr'))
        )
    except TimeoutException:
        chrome_driver.quit()
        return "Taking too long to load..."

    offices = chrome_driver.find_elements(
        By.XPATH, '//section[@id="vvConsolidatedScorecardResults"]//div[@class="vv-tab-menu-item-container"]')

    for office in offices:

        office.click()
        soup = get_soup(chrome_driver)

        for session, records in extract(soup):
            save_extract(records, office.text, session)

        save_html(soup)

    return "Extract success."


if __name__ == '__main__':

    _, EXPORT_DIR, URL, *FILES = sys.argv

    EXPORT_DIR = Path(EXPORT_DIR)

    if FILES:
        extract_from_file(FILES)
    else:
        print(main())
