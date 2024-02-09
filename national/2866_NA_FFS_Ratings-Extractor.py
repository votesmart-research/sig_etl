# This is the webscraping script for Freedom First Society (FFS), sig_id=2866

from datetime import datetime
from pathlib import Path
from collections import defaultdict

import pandas
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup



URL = "https://www.freedomfirstsociety.org/scorecard/"

RATINGS_METHODOLOGY = {'fa-check': '+',
                       'fa-times': '-',
                       'fa-question': '*'}


def extract(page_source, **additional_info):

    soup = BeautifulSoup(page_source, 'html.parser')

    table = soup.find('div', {'id': 'scorecard-wrapper'}).table
    bill_names = [p.text.strip()
                  for p in table.find_all('th')[-1].find_all('p')]
    headers = ['state_id', 'name'] + bill_names
    rows = table.tbody.find_all('tr')

    records = []

    for row in rows:
        columns = row.find_all('td')

        state_id_name = [td.text.strip() for td in columns[:2]]
        scores = [i['class'][-1] for i in columns[2:][-1].find_all('i')]

        translated_scores = [RATINGS_METHODOLOGY[score]
                             if score in RATINGS_METHODOLOGY.keys() else '?' for score in scores]

        record = dict(zip(headers, state_id_name +
                      translated_scores)) | additional_info
        records.append(record)

    return records


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


def main(congress):

    chrome_service = Service()
    chrome_options = Options()
    chrome_options.add_argument('incognito')
    chrome_options.add_argument('headless')
    chrome_driver = webdriver.Chrome(
        service=chrome_service, options=chrome_options)

    chrome_driver.get(URL)

    scorecard_form = WebDriverWait(chrome_driver, 10).until(EC.visibility_of_element_located(
        (By.XPATH, "//div[@ng-show='scorecard.main.visible']")))

    # scorecard_form = chrome_driver.find_element(By.XPATH, "//div[@ng-show='scorecard.main.visible']")

    select_congress = Select(scorecard_form.find_element(
        By.XPATH, "//select[@ng-model='scorecard.selected_congress']"))
    select_session = Select(scorecard_form.find_element(
        By.XPATH, "//select[@ng-model='scorecard.selected_session']"))
    select_office = Select(scorecard_form.find_element(
        By.XPATH, "//select[@ng-model='scorecard.selected_branch']"))
    select_party = Select(scorecard_form.find_element(
        By.XPATH, "//select[@ng-model='scorecard.selected_party']"))
    button_go = scorecard_form.find_element(
        By.XPATH, "//button[@ng-click='scorecard.load_bills()']")

    select_congress.select_by_visible_text(congress)

    records = defaultdict(list)

    for option_s in select_session.options:
        for option_o in select_office.options:
            for option_p in select_party.options:

                option_s.click()
                option_o.click()
                option_p.click()
                button_go.click()
                
                WebDriverWait(chrome_driver, 10).until(EC.presence_of_element_located(
                    (By.XPATH, "//div[@class='col-sm-2 ng-hide']")))

                save_html(chrome_driver.page_source, EXPORT_DIR, option_s.text, option_o.text, option_p.text)

                congress_session = f'{select_congress.first_selected_option.text}-{option_s.text}'
                records[congress_session] += extract(
                    chrome_driver.page_source, office=option_o.text, party=option_p.text)

    for session, record in records.items():
        save_extract(record, EXPORT_DIR, session)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        prog='Freedom First Society ratings Extractor')
    parser.add_argument('-c', '--congress', required=True)
    parser.add_argument('-d', '--exportdir', type=Path, required=True)

    args = parser.parse_args()
    EXPORT_DIR = args.exportdir

    main(args.congress)
