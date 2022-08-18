# This is the webscraping script for Florida Chamber of Commerce, sig_id = 607

import requests
import pandas
from bs4 import BeautifulSoup


URL = "https://reportcard.flchamber.com/"


def main():
    response = requests.get(URL)
    page_source = response.text

    soup = BeautifulSoup(page_source, 'html.parser')

    table = soup.find('table', {'data-id': 'M583577_622182'})

    rows = table.tbody.find_all('tr')
    candidate_list = []

    for row in rows:
        columns = row.find_all('td')

        name = columns[1].text
        office = columns[2].text
        district = columns[3].text
        sig_rating = columns[4].text
        letter_grade = columns[5].text
        

        candidate = {'name': name,  
                    'office': office,
                    'district': district,
                    '2021 rating': sig_rating,
                    'letter grade': letter_grade}

        candidate_list.append(candidate)

    df = pandas.DataFrame.from_records(candidate_list)
    df.to_csv('2022_FL_COC_Ratings-Extract', index=False)
    
if __name__ == "__main__":
    main()
