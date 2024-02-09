# This is the webscraping script for Associated General Contractors of America (AGC), sig_id=503

from pathlib import Path
from urllib.parse import urlparse, urljoin
from datetime import datetime

import pandas
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options


URL = "https://agcscorecard.voxara.net"

TIMESTAMP = datetime.strftime(datetime.now(), '%Y-%m-%d-%H%M')


def extract(page_source):
    """
    Headers
    =======
    agc_candidate_id: Candidate ID assigned to each candidate
    member: {firstname} {lastname}
    chamber: House, Senate
    district: {state_id}-{district, office}
    party: R, D, I
    current: percent
    lifetime: percent
    """

    soup = BeautifulSoup(page_source, 'html.parser')
    table = soup.table

    headers = ['sig_candidate_id'] + [th.get_text(strip=True)
                                      for th in table.thead.find_all('th')]

    def get_text(x): return x.get_text(strip=True)

    extracted = []

    for tr in table.tbody.find_all('tr'):
        candidate_url = urlparse(tr['onclick'].lstrip('document.location=').strip("'"))
        sig_candidate_id = candidate_url.path.rpartition('/')[-1]
        columns = tr.find_all('td')
        columns[0].span.decompose()
        row = [sig_candidate_id] + list(map(get_text, columns))
        extracted.append(dict(zip(headers, row)))

    return extracted


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

    urls = ('/members-house', '/members-senate')

    extracted = []

    for url in urls:
        chrome_driver.get(urljoin(URL, url))
        extracted += extract(chrome_driver.page_source)
        save_html(chrome_driver.page_source, EXPORT_DIR, url.strip('/'))

    save_extract(extracted, EXPORT_DIR)


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(prog='sig_webscrape')
    parser.add_argument(
        'exportdir', help='file directory of where the files exports to')
    parser.add_argument('-f', '--htmldir', help='file directory of html files')

    args = parser.parse_args()
    EXPORT_DIR = args.exportdir

    main()
