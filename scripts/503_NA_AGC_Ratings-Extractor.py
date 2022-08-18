# This is the webscraping script for Associated General Contractors of America (AGC), sig_id=503

import os
import requests
import pandas

from datetime import datetime
from bs4 import BeautifulSoup


MAIN_URL = "https://agcscorecard.voxara.net"
PARAMETERS = {'session': 'search-congress',
              'party': 'search-party',
              'state': 'search-state'}


def extract(response):

    """
    Headers
    =======
    MEMBER: {firstname} {lastname}
    CHAMBER: House, Senate
    DISTRICT: {state_id}-{district, office}
    PARTY: R, D, I
    CURRENT: percent
    LIFETIME: percent
    """

    soup = BeautifulSoup(response.text, 'html.parser')
    headers = ['agc_candidate-id'] + list(map(lambda th: th.text.strip(), soup.table.thead.find_all('th')))
    rows = soup.table.tbody.find_all('tr')

    records = []

    for row in rows:
        agc_candidate_id = row['onclick'].split('/')[-1].split('?')[0].strip()
        row.td.span.decompose()
        columns = [agc_candidate_id] + list(map(lambda td: td.text.strip(), row.find_all('td')))
        records.append(dict(zip(headers, columns)))

    return records


def download_page(response):
    soup = BeautifulSoup(response.text, 'html.parser')
    office = response.url.split('/')[-1].split('-')[-1]
    timestamp = datetime.now().strftime('%Y-%m-%d')

    if not os.path.isdir(f"{SCRIPT_DIR}/{GROUP_ABV}_HTML"):
        os.mkdir(f"{SCRIPT_DIR}/{GROUP_ABV}_HTML")

    with open(f"{SCRIPT_DIR}/{GROUP_ABV}_HTML/_NA_{GROUP_ABV}_Ratings_{office}-{timestamp}.html", 'w') as f:
        f.write(soup.prettify())


def main():
    response_senate = requests.get(f"{MAIN_URL}/members-senate")
    response_house = requests.get(f"{MAIN_URL}/members-house")

    senate_records = extract(response_senate)
    house_records = extract(response_house)

    download_page(response_senate)
    download_page(response_house)

    df = pandas.DataFrame.from_records(senate_records + house_records)
    df.to_csv(f"_NA_{GROUP_ABV}_Ratings-Extract.csv", index=False)

 
if __name__ == "__main__":
    SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
    GROUP_ABV = 'AGC'
    SIG_ID = 503

    main()