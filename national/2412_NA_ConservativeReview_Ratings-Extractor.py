
import re
from datetime import datetime
from pathlib import Path

import pandas
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

URL = "https://libertyscore.conservativereview.com/"


def extract(page_source):

    soup = BeautifulSoup(page_source, 'html.parser')

    table = soup.find('table', {'id': 'repsTable'})
    headers = [th.div.text for th in table.thead.find_all('th')]

    rows = [tr.find_all('td') for tr in table.tbody.find_all('tr')]
    def get_text(x): return x.text.strip()
    extracted = []

    for row in rows:
        info_1 = dict(zip(headers[:2], map(get_text, row[:2])))
        party = re.sub(r".svg|.png", "", row[2].img['src'].split('/')[-1])
        info_2 = dict(zip(headers[3:], map(get_text, row[3:])))
        extracted.append(info_1 | {'party': party} | info_2)

    return extracted


def extract_files(files: list):

    extracted = []

    for file in files:
        with open(file, 'r') as f:
            extracted += extract(f.read())


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
    chrome_options = Options()
    chrome_options.add_argument('incognito')
    chrome_options.add_argument('headless')
    chrome_driver = webdriver.Chrome(
        service=chrome_service, options=chrome_options)

    chrome_driver.get(URL)

    WebDriverWait(chrome_driver, 10).until(
        EC.presence_of_element_located((By.ID, 'repsTable'))
    )

    # close overlay
    ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

    save_html(chrome_driver.page_source, EXPORT_DIR)
    extracted = []

    while True:
        next_button = chrome_driver.execute_script(
            """
            return document.querySelector("button[aria-label='Go to next page']")
            """)

        if next_button:
            next_button.click()
            extracted += extract(chrome_driver.page_source)
            save_html(chrome_driver.page_source, EXPORT_DIR)
        else:
            break

    return extracted

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(prog='sig_webscrape')
    parser.add_argument(
        'exportdir', help='file directory of where the files exports to')
    parser.add_argument('-f', '--htmldir', help='file directory of html files')

    args = parser.parse_args()

    EXPORT_DIR = Path(args.exportdir)

    if args.htmldir:
        html_dir = Path(args.htmldir)
        html_files = filter(lambda f: f.name.endswith(
            '.html'), (EXPORT_DIR/html_dir).iterdir())
        extracted = extract_files(
            sorted(html_files, key=lambda x: x.stat().st_ctime))
    else:
        extracted = main()

    save_extract(extracted, EXPORT_DIR)
