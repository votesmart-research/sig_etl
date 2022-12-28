# This is the webscraping script for Libertas Institute , sig_id =  2414

import pandas
from selenium import webdriver
from bs4 import BeautifulSoup


URL = "https://libertas.org/resources/legislator-indexes/2021-index/"

def extract(table):
    header = []
    for th in table.thead.find_all('th'):
        if th.span:
            th.span.decompose()
        
        header.append(th.text)
        
    rows = [tr.find_all('td') for tr in table.tbody.find_all('tr')]

    get_text = lambda x: x.text.strip()

    return [dict(zip(header, map(get_text, row))) for row in rows]


def main():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('incognito')
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(URL)
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    table_house = soup.find('table', {'id': 'index_house'})
    table_senate = soup.find('table', {'id': 'index_senate'})
    extracted = extract(table_house) + extract(table_senate)

    df = pandas.DataFrame.from_records(extracted)
    df.to_csv('2021_UT_LI_Ratings-Extract.csv', index=False)


if __name__ == "__main__":
    main()
