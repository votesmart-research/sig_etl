# This is the webscraping script for Pennsylvania Chamber of Business and Industry, sig_id = 1307

import pandas
from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup


URL = "https://www.pachamber.org/advocacy/chamber_pac/legislative_scorecard/"

def extract(table, candidate_list):
    rows = table.tbody.find_all('tr')
    
    for row in rows:
        columns = row.find_all('td')

        candidate = {'name': columns[0].text,  
                    'district': columns[1].text,
                    'party': columns[2].text,
                    '2021-2022 rating': columns[3].text,
                    'lifetime score': columns[4].text,
                    'candidate ID': row['leg_vv_id'],
                    }

        candidate_list.append(candidate)

    return 


def main():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('incognito')
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(URL)
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    table_senate = soup.find('table', {'class': 'legislative_scorecard'})
    table_house = soup.find('div', {'id': "State House Scorecard"})
    
    candidate_list=[]
    extract(table_house, candidate_list)
    extract(table_senate, candidate_list)

    df = pandas.DataFrame.from_records(candidate_list)
    df.to_csv('2022_PA_PCBI_Ratings-Extract.csv', index=False)


if __name__ == "__main__":
    main()
