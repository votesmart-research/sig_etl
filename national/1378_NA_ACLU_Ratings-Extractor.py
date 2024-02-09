# This is the webscrape for American Civil Liberties Union (ACLU), sig_id=1378

import re
import time
import pandas


from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup


URL = "https://www.aclu.org/scorecard/?filter=all"


def extract(soup):

    all_states = soup.find_all('div', {'class': 'state-results'})

    records = []

    for state in all_states:

        candidates = state.find_all('a')
            
        for candidate in candidates:

            score = candidate.find('p', {'class': 'score'})
            party = candidate.find('div', {'class': 'party'})
            name = candidate.find('div', {'class': 'name'})
            district = candidate.find('div', {'class': 'office'})

            records.append({'name': name.text.strip() if name else None,
                            'party': party.text.strip() if party else None,
                            'district': district.text.strip() if district else None,
                            'score': score.text.strip() if score else None,
                            'state': state.h3.text.strip() if state.h3 else None})

    return records


def main():

    chrome_service = Service('chromedriver')
    chrome_options = Options()
    chrome_options.add_argument('incognito')
    chrome_options.add_argument('headless')
    chrome_driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    chrome_driver.get(URL)

    html = chrome_driver.find_element(By.TAG_NAME, 'html')

    counter = 0

    while True:

        html.send_keys(Keys.END)

        time.sleep(0.75)

        soup = BeautifulSoup(chrome_driver.page_source, 'html.parser')
        temp_counter = len(soup.find_all('div', {'class': 'state-results'}))

        if not(temp_counter - counter):
            break
        
        counter += temp_counter - counter

    congress = "".join(re.findall(r'\d+', soup.find('h2', {'class':'results-summary'}).text))

    with open("_NA_ACLU_Ratings.html", 'w') as f:
        f.write(soup.prettify())

    extracted = extract(soup)

    df = pandas.DataFrame.from_records(extracted)
    df.to_csv(f'{congress}_NA_ACLU_Ratings-Extract.csv', index=False)
        
    
if __name__ == '__main__':
    main()