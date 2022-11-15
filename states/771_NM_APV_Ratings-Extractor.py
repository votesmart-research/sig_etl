# This is the webscraping script for Animal Protection Voters, sig_id = 771

import requests
import pandas
from bs4 import BeautifulSoup


URL = "https://apvnm.org/scorecards/house-scores/"


def extract_table(soup):

    table = soup.find('table', {'id': 'tablepress-12'})
    header = [th.text for th in table.thead.find_all('th')]
    rows = [tr.find_all('td') for tr in table.tbody.find_all('tr')]

    get_text = lambda x: x.text

    return [dict(zip(header, map(get_text, row))) for row in rows]


def main():
    
    response = requests.get(URL)
    page_source = response.text

    soup = BeautifulSoup(page_source, 'html.parser')
   
    extracted = extract_table(soup)
        
    df = pandas.DataFrame.from_records(extracted)
    df.to_csv('_NM_APV_Ratings-Extract.csv', index=False)
    
    
if __name__ == "__main__":
    main()
