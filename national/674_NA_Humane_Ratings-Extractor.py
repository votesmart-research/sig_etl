
import time
from datetime import datetime
from pathlib import Path


import pandas
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tqdm import tqdm


URL = "https://hslf.org/current_scorecard"


def extract(page_source):

    soup = BeautifulSoup(page_source, 'html.parser')

    rep_container = soup.find('div', {'id': 'rep'})
    info_container = rep_container.find(
        'div', {'class': 'detail'}) if rep_container else None
    info = info_container.find(
        'span', {'class': 'eyebrow'}) if info_container else None
    name = info_container.find('h2') if info_container else None

    score_container = rep_container.find('div', {'class': 'score'})
    score_heading = [strong.get_text(strip=True)
                     for strong in score_container.find_all('strong')]
    score_text = [em.get_text(strip=True)
                  for em in score_container.find_all('em')]
    scores = dict(zip(score_heading, score_text))

    return {'name': name.get_text(strip=True) if name else None,
            'info': info.get_text(strip=True) if info else None} | scores


def extract_files(files: list):

    extracted = []

    for file in files:
        with open(file, 'r') as f:
            extracted.append(extract(f.read()))

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
    rows = WebDriverWait(chrome_driver, 10).until(EC.presence_of_all_elements_located(
        (By.XPATH, "//table[@class='scorecard_table']/tbody/tr")))

    filtered_rows = filter(
        lambda tr: 'state-label' not in tr.get_attribute('class'), rows)

    extracted = []
    for tr in tqdm(list(filtered_rows)):
        row = WebDriverWait(chrome_driver, 10).until(EC.visibility_of_element_located(
            (By.XPATH, f"//tr[@id='{tr.get_attribute('id')}']")
        ))
        row.click()
        extracted.append(extract(chrome_driver.page_source))
        save_html(chrome_driver.page_source, export_dir)
        time.sleep(0.8)
        back_to_list = WebDriverWait(chrome_driver, 10).until(EC.visibility_of_element_located(
            (By.XPATH, "//a[@class='back-to-list']")))
        back_to_list.click()
        time.sleep(1)

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
