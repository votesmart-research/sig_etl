# This is the webscraping script for California League of Conservation Voters, sig_id = 495

import requests
import pandas
from bs4 import BeautifulSoup


DOMAIN_URL = "https://envirovoters.org"
RATINGS_PAGE  = "/scorecard"
SENATE_PAGE = "/senate"
ASSEMBLY_PAGE = "/house"
GOVERNOR_PAGE = "/representative/gavin-newsom"


def extract(URL):
    
    response = requests.get(URL)
    page_source = response.text
    candidate_list = []

    soup = BeautifulSoup(page_source, 'html.parser')
    table = soup.find('table', {'class': 'scorecard-table hide-first-heading'})
    rows = table.tbody.find_all('tr')

    for row in rows:
        columns = row.find_all('td')
        candidate = {
            'name': columns[0].text,  
            'party': columns[1].text,
            'district': columns[2].text,
            '2021 rating': columns[3].text,
            'lifetime rating': columns[4].text
            }

        candidate_list.append(candidate)

    return candidate_list


def extract_candidate_page(URL):

    response = requests.get(URL)
    page_source = response.text

    soup = BeautifulSoup(page_source, 'html.parser')

    name = soup.find('h1', {'class':'rep-name'})
    party = soup.find('li', {'class':'party'})
    current_score = soup.find('h2', {'class':'current-score'})
    lifetime_score = soup.find('li', {'class':'lifetime-score'})
    district = soup.find('li', {'class':'district'})

    district_header = district.strong.text if district else None
    current_score_header = current_score.span.previous_sibling.text
    lifetime_score_header = lifetime_score.strong.next_sibling.text

    record = {'name': name.text,  
              'party': party.strong.next_sibling.text,
              district_header: district_header.next_sibling.text if district_header else None,
              current_score_header: current_score.span.text,
              lifetime_score_header: lifetime_score.strong.text}

    return record
    

def main():

    # senate_records = extract(f"{DOMAIN_URL}{RATINGS_PAGE}{SENATE_PAGE}")
    # assembly_records = extract(f"{DOMAIN_URL}{RATINGS_PAGE}{ASSEMBLY_PAGE}")

    print(extract_candidate_page(f"{DOMAIN_URL}{RATINGS_PAGE}{GOVERNOR_PAGE}"))

    # df = pandas.DataFrame.from_records(senate_records + assembly_records)
    # df.to_csv('2021_CA_EV_Ratings-Extract.csv', index=False)


if __name__ == "__main__":
    main()
