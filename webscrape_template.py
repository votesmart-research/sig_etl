
from datetime import datetime
from pathlib import Path


import pandas
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException


URL = ""


def extract(page_source, **additional_info):

    soup = BeautifulSoup(page_source, 'html.parser')

    def extract_table(table):

        headers = [th.get_text(strip=True)
                   for th in table.thead.find_all('th')]
        rows = [tr.find_all('td') for tr in table.tbody.find_all('tr')]

        def get_text(x): return x.get_text(strip=True)

        return [dict(zip(headers, map(get_text, row))) | additional_info for row in rows]

    return soup


def extract_files(files: list):

    extracted = []

    for file in files:

        with open(file, 'r') as f:
            extracted += extract(f.read())

    return extracted


def save_html(page_source, filepath, *additional_info):

    soup = BeautifulSoup(page_source, 'html.parser')

    filepath = Path(filepath) / 'HTML_FILES'
    filepath.mkdir(exist_ok=True)

    timestamp = datetime.strftime(datetime.now(), '%Y-%m-%d-%H%M%S-%f')

    with open(filepath / f"Ratings_{'-'.join(map(str, additional_info))}"
                         f"{'-' if additional_info else ''}{timestamp}.html", 'w') as f:
        f.write(str(soup))


def save_extract(extracted: list[dict], filepath, *additional_info):

    filepath = Path(filepath) / 'EXTRACT_FILES'
    filepath.mkdir(exist_ok=True)

    timestamp = datetime.strftime(datetime.now(), '%Y-%m-%d-%H%M%S-%f')

    df = pandas.DataFrame.from_records(extracted)
    df.to_csv(
        filepath / f"Ratings-Extract_{'-'.join(map(str, additional_info))}"
                   f"{'-' if additional_info else ''}{timestamp}.csv", index=False)


def main(export_dir):

    chrome_service = Service()
    chrome_options = Options()
    chrome_options.add_argument('incognito')
    chrome_options.add_argument('headless')
    chrome_driver = webdriver.Chrome(
        service=chrome_service, options=chrome_options)

    chrome_driver.get(URL)

    # close overlay
    ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

    extracted = extract(chrome_driver.page_source)

    save_html(chrome_driver.page_source, export_dir)

    return extracted


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(prog='sig_webscrape')
    parser.add_argument('-u', '--url', type=Path, required=True,
                        help='website url where the ratings are located')
    parser.add_argument('-e', '--exportdir', type=Path, required=True,
                        help='file directory of where the files exports to')
    parser.add_argument('-f', '--htmldir', type=Path,
                        help='file directory of html files to read')

    args = parser.parse_args()
    
    URL = args.url

    if args.htmldir:
        html_files = filter(lambda f: f.name.endswith(
            '.html'), (args.exportdir / args.htmldir).iterdir())
        extracted = extract_files(
            sorted(html_files, key=lambda x: x.stat().st_ctime))
    else:
        extracted = main(args.exportdir)

    save_extract(extracted, args.exportdir)