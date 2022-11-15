# This is the webscraping script for Associated General Contractors of America (AGC), sig_id=503

import os
import sys
import requests
import pandas

from datetime import datetime
from bs4 import BeautifulSoup
from tqdm import tqdm


GROUP_ABV = 'AGC'
SIG_ID = 503
MAIN_URL = "https://agcscorecard.voxara.net"

PARAMETERS = {'session': 'search-congress',
              'party': 'search-party',
              'state': 'search-state'}

TIMESTAMP = datetime.strftime(datetime.now(), '%Y-%m-%d-%H%M')


def extract(response):

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

    soup = BeautifulSoup(response.text, 'html.parser')
    headers = ['agc_candidate_id'] + list(map(lambda th: th.text.strip().lower(), 
                                        soup.table.thead.find_all('th')))

    rows = soup.table.tbody.find_all('tr')

    records = []

    for row in tqdm(rows, desc=f'Extracting from {response.url}'):
        agc_candidate_id = row['onclick'].split('/')[-1].split('?')[0].strip()
        row.td.span.decompose()
        columns = [agc_candidate_id] + list(map(lambda td: td.text.strip(), 
                                                row.find_all('td')))
        records.append(dict(zip(headers, columns)))

    return records


def save_page(response):

    soup = BeautifulSoup(response.text, 'html.parser')
    office = response.url.split('/')[-1].split('-')[-1].title()

    if not os.path.isdir(f"{EXPORTDIR}/HTML_FILES"):
        os.mkdir(f"{EXPORTDIR}/HTML_FILES")

    with open(f"{EXPORTDIR}/HTML_FILES/{TIMESTAMP}_NA_{GROUP_ABV}_Ratings_{office}.html", 'w') as f:
        f.write(soup.prettify())


def main():

    response_senate = requests.get(f"{MAIN_URL}/members-senate")
    response_house = requests.get(f"{MAIN_URL}/members-house")

    senate_records = extract(response_senate)
    house_records = extract(response_house)

    save_page(response_senate)
    save_page(response_house)

    df = pandas.DataFrame.from_records(senate_records + house_records)
    df.to_csv(f"{EXPORTDIR}/{TIMESTAMP}_NA_{GROUP_ABV}_Ratings-Extract.csv", index=False)

 
if __name__ == "__main__":

    _, EXPORTDIR = sys.argv
    EXPORTDIR = EXPORTDIR if os.path.isdir(EXPORTDIR) else os.path.dirname(EXPORTDIR)

    main()