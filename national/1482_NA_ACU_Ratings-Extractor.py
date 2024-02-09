# This is the webscraping script for American Conservative Union (ACU), sig_id=1482

from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin

import pandas
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
from tqdm import tqdm


URL = "http://ratings.conservative.org/people"


"""
Filters:

Year (year): The year that the rating is in
State (state): Shows the state that the legislators are in
Party (party): 'R'(republican), 'D'(democratic), 'I'(independent)
Office (chamber): 'H'(house), 'S'(senate), 'A'(assembly)
Results per page (limit): How many results of legislators to show on page, 'all' for everything.
Coverage (level): 'federal' or 'state' or 'both'

"""

# All 50 states and 'US' for nationwide
STATES = ['AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
          'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
          'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
          'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
          'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
          'US']


def url_query(**filters):
    query = '&'.join((f"{k}={v}" for k, v in filters.items()))
    return urljoin(URL, f"?{query}")


def extract(page_source, **additional_info):

    soup = BeautifulSoup(page_source, 'html.parser')
    rows = soup.find_all('div', {'class': 'sc-hzDkRC'})

    records = []

    for row in rows:

        name_party, other_info = row.find(
            'div', {'class': 'sc-fBuWsC'}).find_all('p')
        rating = row.find('span', {'class': 'sc-gipzik'})
        lifetime_rating = row.find('div', {'class': 'sc-gPEVay'})

        records.append({'sig_candidate_id': row.a['href'].rpartition('/')[-1],
                        'name_party': name_party.get_text(strip=True),
                        'other_info': other_info.get_text(strip=True),
                        'rating': rating.get_text(strip=True) if rating else None,
                        'lifetime_rating': lifetime_rating.get_text(strip=True) if lifetime_rating else None,
                        } | additional_info)

    return records


def save_extract(extracted: list[dict], filepath, *additional_info):

    filepath = Path(filepath) / 'EXTRACT_FILES'
    filepath.mkdir(exist_ok=True)

    timestamp = datetime.strftime(datetime.now(), '%Y-%m-%d-%H%M%S-%f')

    df = pandas.DataFrame.from_records(extracted)
    df.to_csv(
        filepath / f"Ratings-Extract_{'-'.join(map(str, additional_info))}"
                   f"{'-' if additional_info else ''}{timestamp}.csv", index=False)


def save_html(page_source, filepath, *additional_info):
    soup = BeautifulSoup(page_source, 'html.parser')

    filepath = Path(filepath) / 'HTML_FILES'
    filepath.mkdir(exist_ok=True)

    timestamp = datetime.strftime(datetime.now(), '%Y-%m-%d-%H%M%S-%f')

    with open(filepath / f"Ratings_{'-'.join(map(str, additional_info))}"
                         f"{'-' if additional_info else ''}{timestamp}.html", 'w') as f:
        f.write(str(soup))


def main(year, export_dir, states):

    chrome_service = Service()
    chrome_options = Options()
    chrome_options.add_argument('incognito')
    chrome_options.add_argument('headless')
    chrome_driver = webdriver.Chrome(
        service=chrome_service, options=chrome_options)

    extracted = []

    p_bar = tqdm(states, desc='State')

    for state in states:
        
        p_bar.desc = state

        url_with_query = url_query(year=year, state=state, limit='all', level='state')

        chrome_driver.get(url_with_query)

        try:
            WebDriverWait(chrome_driver, 30).until(
                EC.visibility_of_element_located(
                    (By.XPATH, "//div[@class='sc-kXeGPI lmbiWA']"))
            )

        except TimeoutException:
            print(f"{state} has a timeout.")
            continue

        extracted += extract(chrome_driver.page_source, state=state)
        save_html(chrome_driver.page_source, export_dir, state)

        p_bar.update(1)

    if extracted:
        save_extract(extracted, export_dir)

    chrome_driver.quit()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        prog='American Conservative Union ratings extractor')
    
    parser.add_argument('-y', '--year', type=int, required=True)
    parser.add_argument('-d', '--exportdir', type=Path, required=True)
    parser.add_argument('-s', '--states', nargs='*')
    parser.add_argument('-f', '--files', type=Path)

    args = parser.parse_args()

    main(args.year, args.exportdir, states=args.states or STATES)
