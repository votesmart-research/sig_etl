# This is the webscraping script for Progressive Punch, sig_id=2167

import os
import pandas
import requests
from bs4 import BeautifulSoup


URL = "https://www.progressivepunch.org/scores.htm"
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))


def extract(soup):
    header_section, body = soup.find_all('table', {'id': 'all-members'})
    
    info_headers = header_section.find('tr', {'class': 'heading'}).find_all('td')
    sub_headers = header_section.find('tr', {'class': 'subheading'}).find_all('td')

    header_text = list(map(lambda td: td.text.strip() if td else None, info_headers[:4] + sub_headers[6:8]))

    rows = body.find_all('tr')

    records = []

    for row in rows:
        columns = row.find_all('td')
        column_text = [td.text.strip() for td in columns[:4] + columns[6:8]]
        records.append(dict(zip(header_text, column_text)))

    return records


def main():

    page_source = requests.get(URL).text
    soup = BeautifulSoup(page_source, 'html.parser')

    with open(f"{SCRIPT_DIR}/_NA_ProgressivePunch_Ratings.html", 'w') as f:
        f.write(soup.prettify())

    records = extract(soup)

    df = pandas.DataFrame.from_records(records)
    df.to_csv(f"{SCRIPT_DIR}/_NA_ProgressivePunch_Ratings-Extract.csv", index=False)


if __name__ == "__main__":
    main()

