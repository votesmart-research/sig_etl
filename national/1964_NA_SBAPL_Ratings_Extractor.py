# This is the webscraping script for Susan B. Anthony List, sig_id = 1964

import pandas
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import ElementNotInteractableException
from bs4 import BeautifulSoup


URL = "https://sbaprolife.org/scorecard"

def extract(table, candidate_list):
    rows = table.tbody.find_all('tr')

    for row in rows:
        columns = row.find_all('td')

        candidate = {'name': columns[0].text,  
                    'state': columns[1].text,
                    'party': columns[2].text,
                    'rating': columns[3].text,
                    }

        candidate_list.append(candidate)

    return


def main():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('incognito')
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(URL)
    
    senate_entries = Select(driver.find_element(By.XPATH, "//select[@name='sc_dt_sen_length']"))
    senate_entries.select_by_value('100')
    house_entries = Select(driver.find_element(By.XPATH, "//select[@name='sc_dt_house_length']"))
    house_entries.select_by_value('100')

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    table_senate = soup.find('table', {'id': 'sc_dt_sen'})
    candidate_list = []
    extract(table_senate, candidate_list)

    while True:
        house_next = driver.find_element(By.ID, "sc_dt_house_next")

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        table_house = soup.find('table', {'id': 'sc_dt_house'})

        extract(table_house, candidate_list)

        if not 'disabled' in house_next.get_attribute('class'):
            house_next.find_element(By.TAG_NAME, "a").click()

        else:
           break

    df = pandas.DataFrame.from_records(candidate_list)
    df.to_csv('2022_NA_SBAPLA_Ratings-Extract.csv', index=False)


if __name__ == "__main__":
    main()
