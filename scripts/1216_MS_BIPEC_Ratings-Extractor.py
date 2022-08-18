# This is the webscraping script for Business & Industry Political Education Committee, sig_id = 1216

import requests
import pandas
from bs4 import BeautifulSoup


DOMAIN_URL = "https://www.bipec.org/reportcards/2022/"

def get_table(URL):
    response = requests.get(URL)
    page_source = response.text

    soup = BeautifulSoup(page_source, 'html.parser')

    table = soup.find('table', {'id': 'example'})

    return table

def extract(table):

    header = [th.text for th in table.thead.find_all('th')]
    rows = [table.tbody.find_all('tr')]

    for row in rows:
        methodology = {'glyphicon-ok': '+', 'glyphicon-remove': '-'}
        row[4:] = methodology(row)

    get_text = lambda x: x.text.strip()

    return [dict(zip(header, map(get_text, row))) for row in rows]

def main():
    table_house = get_table(DOMAIN_URL + "href=?c=house")
    table_senate = get_table(DOMAIN_URL + "href=?c=senate")

    extracted = extract(table_house) + extract(table_senate)

    df = pandas.DataFrame.from_records(extracted)
    df.to_csv('BIPEC_Ratings-Extract.csv', index=False)
    
if __name__ == "__main__":
    main()
