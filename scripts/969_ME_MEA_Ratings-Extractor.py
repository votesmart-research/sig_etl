# This is the webscraping script for Maine Education Association, sig_id = 969

import requests
import pandas
from bs4 import BeautifulSoup


URL = "https://maineea.org/2021-scorecard/"

def extract(soup, table):
    header = [th.text for th in table.thead.find_all('th')]
    rows = [tr.find_all('td') for tr in table.tbody.find_all('tr')]

    get_text = lambda x: x.text

    return [dict(zip(header, map(get_text, row))) for row in rows]



def main():
    response = requests.get(URL)
    page_source = response.text

    soup = BeautifulSoup(page_source, 'html.parser')
    
    table = soup.find('table', {'id': 'tablepress-84'})
    extract_house = extract(soup, table)

    table = soup.find('table', {'id': 'tablepress-85'})
    extract_senate = extract(soup, table)

    df_house = pandas.DataFrame.from_records(extract_house)
    df_house.to_csv('ME_MEA_Ratings-Extract_House.csv', index=False)

    df_senate = pandas.DataFrame.from_records(extract_senate)
    df_senate.to_csv('ME_MEA_Ratings-Extract_Senate.csv', index=False)
    
if __name__ == "__main__":
    main()
