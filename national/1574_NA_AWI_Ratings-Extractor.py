
import pandas

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait, Select

from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path


URL = "https://awionline.org/compassion-index#/legislators"


def extract(page_source):

    soup = BeautifulSoup(page_source, 'html.parser')
    table = soup.find('table', {'class': 'congressweb-module-listTable'})

    headers = [th.get_text(strip=True) for th in table.find_all('th')]
    rows = [tr.find_all('td') for tr in table.find_all('tr')[1:]]

    def get_text(x): return x.get_text(strip=True, separator=' ')

    return [dict(zip(headers, map(get_text, row))) for row in rows]


def extract_files(files: list):

    extracted = []

    for file in files:

        with open(file, 'r') as f:
            extracted += extract(f.read())

    return extracted


def save_html(page_source, filepath=None):

    soup = BeautifulSoup(page_source, 'html.parser')
    filepath = Path(filepath) / \
        'HTML_FILES' if filepath else Path('HTML_FILES')
    filepath.mkdir(exist_ok=True)

    timestamp = datetime.strftime(datetime.now(), '%Y-%m-%d-%H%M%S-%f')

    with open(filepath / f"Ratings_{timestamp}.html", 'w') as f:
        f.write(str(soup))


def save_extract(extracted: dict[dict], filepath=None, *additional_info):

    filepath = Path(filepath) / \
        'EXTRACT_FILES' if filepath else Path('EXTRACT_FILES')
    filepath.mkdir(exist_ok=True)

    timestamp = datetime.strftime(datetime.now(), '%Y-%m-%d-%H%M%S-%f')

    df = pandas.DataFrame.from_records(extracted)
    df.to_csv(
        filepath / f"Ratings-Extract_{'-'.join(map(str, additional_info))}-{timestamp}.csv", index=False)


def main():

    chrome_service = Service('chromedriver')
    chrome_options = Options()
    chrome_options.add_argument('incognito')
    # chrome_options.add_argument('headless')
    chrome_driver = webdriver.Chrome(
        service=chrome_service, options=chrome_options)

    chrome_driver.get(URL)

    to_select = ['118-Senate', '118-House']

    # close overlay
    ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

    extracted = []

    for session in to_select:

        chrome_driver.refresh()

        iframe = WebDriverWait(chrome_driver, 10).until(EC.presence_of_element_located(
            (By.XPATH, "//div[@id='iframe']//iframe")))

        chrome_driver.switch_to.frame(iframe)

        select = Select(chrome_driver.find_element(
            By.XPATH, "//select[@name='congress_chamber']"))
        button = chrome_driver.find_element(
            By.XPATH, "//form[@action='/AWI/legislators/membercompassionindex']//input[@class='congressweb-button']")

        select.select_by_value(session)
        button.click()

        WebDriverWait(chrome_driver, 10).until(EC.presence_of_element_located(
            (By.XPATH, "//table[@class='congressweb-module-listTable']")
        ))

        extracted += extract(chrome_driver.page_source)
        save_html(chrome_driver.page_source, export_dir)

    return extracted


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(prog='sig_webscrape')
    parser.add_argument(
        'exportdir', help='file directory of where the files exports to')
    parser.add_argument('-f', '--htmldir', help='file directory of html files')

    args = parser.parse_args()
    export_dir = Path(args.exportdir)

    if args.htmldir:
        html_dir = Path(args.htmldir)
        html_files = filter(lambda f: f.name.endswith(
            '.html'), (export_dir/html_dir).iterdir())
        extracted = extract_files(
            sorted(html_files, key=lambda x: x.stat().st_ctime))
    else:
        extracted = main()

    save_extract(extracted, export_dir)
