# This is the webscraping script for Freedom First Society (FFS), sig_id=2866

import os
import time
import pandas

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from bs4 import BeautifulSoup
from collections import defaultdict


URL = "https://www.freedomfirstsociety.org/scorecard/"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__name__))
CHROMEDRIVER_PATH = os.path.abspath(SCRIPT_DIR + '/chromedriver')


def extract(soup, other_info):

    table = soup.find('div', {'id': 'scorecard-wrapper'}).table

    bill_names= [p.text.strip() for p in table.find_all('th')[-1].find_all('p')]

    headers = ['state_id', 'name'] + bill_names
    rows = table.tbody.find_all('tr')
    
    methodology = {'fa-check': '+', 'fa-times':'-', 'fa-question':'*'}
    
    records = []

    for row in rows:
        columns = row.find_all('td')

        state_id_name = [td.text.strip() for td in columns[:2]]
        scores = [i['class'][-1] for i in columns[2:][-1].find_all('i')]

        translated_scores = [methodology[score] if score in methodology.keys() else '?' for score in scores]

        record = dict(zip(headers, state_id_name + translated_scores))

        record.update(other_info)

        records.append(record)

    return records


def main():

    chrome_service = Service('chromedriver')
    chrome_options = webdriver.ChromeOptions()

    chrome_options.add_argument('incognito')

    driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    driver.get(URL)

    time.sleep(5)

    scorecard_form = driver.find_element(By.XPATH, "//div[@ng-show='scorecard.main.visible']")

    select_congress = Select(scorecard_form.find_element(By.XPATH, "//select[@ng-model='scorecard.selected_congress']"))
    select_session = Select(scorecard_form.find_element(By.XPATH, "//select[@ng-model='scorecard.selected_session']"))
    select_office = Select(scorecard_form.find_element(By.XPATH, "//select[@ng-model='scorecard.selected_branch']"))
    select_party = Select(scorecard_form.find_element(By.XPATH, "//select[@ng-model='scorecard.selected_party']"))
    button_go = scorecard_form.find_element(By.XPATH, "//button[@ng-click='scorecard.load_bills()']")

    select_congress.select_by_visible_text('116')

    records = defaultdict(list)

    for option_s in select_session.options:
        for option_o in select_office.options:
            for option_p in select_party.options:

                option_s.click()
                option_o.click()
                option_p.click()
                button_go.click()

                time.sleep(5)

                soup = BeautifulSoup(driver.page_source, 'html.parser')

                state_party = {'state': option_o.text, 'party': option_p.text}

                records[f'{select_congress.first_selected_option.text}-{option_s.text}'] += extract(soup, other_info=state_party)

    for sheetname, record in records.items():
        df = pandas.DataFrame.from_records(record)
        df.to_csv(f'{sheetname}_NA_FFS_Ratings-Extract.csv', index=False)


if __name__ == "__main__":
    main()