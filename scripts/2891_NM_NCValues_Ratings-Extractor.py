# This is the web-scraping script for North Carolina Values Coalition, sig_id = 2891

import requests
import pandas
from bs4 import BeautifulSoup


URL = "https://www.ncvalues.org/scorecard_frame"

def main():
    
    response = requests.get(URL)
    page_source = response.text

    soup = BeautifulSoup(page_source, 'html.parser')
    table = soup.find('table', {'id': 'myTable'})

    rows = table.tbody.find_all('tr')

    candidate_list = []

    for row in rows:
        columns = row.find_all('td')

        sig_rating = columns[1].text
        name = columns[2].text
        district = columns[6].text
        office = columns[8].text
        

        candidate = {'name': name,  
                    'district': district,
                    'office': office, 
                    '2022 rating': sig_rating}

        candidate_list.append(candidate)
        
    df = pandas.DataFrame.from_records(candidate_list)
    df.to_csv('2022_NC_NCVC_Ratings-Extract.csv', index=False)
    
if __name__ == "__main__":
    main()
