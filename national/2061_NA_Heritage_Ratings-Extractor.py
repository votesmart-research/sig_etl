# This is the webscraping script for Heritage Action for America, sig_id=2061

from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, urljoin

import pandas
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from tqdm import tqdm


URL = "https://heritageaction.com/scorecard/members"


def extract_scores(page_source):

    soup = BeautifulSoup(page_source, 'html.parser')

    scores = soup.find_all('div', {'class': 'member-stats__item'})
    scores_text = {
        score.span.get_text(strip=True): score.div.get_text(strip=True)
        for score in scores[:2]
    }

    return scores_text


def extract_info(page_source):

    soup = BeautifulSoup(page_source, 'html.parser')
    table = soup.find('table')

    headers = ['sig_candidate_id'] + \
              [th.get_text(strip=True) for th in soup.thead.find_all('th')[:-2]] + \
              ['candidate_url']

    def get_text(x): return x.get_text(strip=True)

    extracted = []

    for tr in table.tbody.find_all('tr'):
        columns = tr.find_all('td')[:-2]
        candidate_url = urlparse(urljoin(URL, columns[0].a['href']))
        sig_candidate_id = candidate_url.path.strip('/').split('/')[-2]
        row = [sig_candidate_id] + \
            list(map(get_text, columns)) + \
            [candidate_url.geturl()]

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

    chrome_driver.get(URL)

    candidate_info = extract_info(chrome_driver.page_source)
    save_html(chrome_driver.page_source, EXPORT_DIR)

    records = []

    for info in tqdm(candidate_info):
        chrome_driver.get(info['candidate_url'])
        records.append(info | extract_scores(chrome_driver.page_source))

        save_html(chrome_driver.page_source,
                  EXPORT_DIR, info['sig_candidate_id'])

    save_extract(records, EXPORT_DIR)


if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser(prog='sig_webscrape')
    parser.add_argument(
        'exportdir', help='file directory of where the files exports to')
    parser.add_argument('-f', '--htmldir', help='file directory of html files')

    args = parser.parse_args()

    EXPORT_DIR = Path(args.exportdir)

    main()
