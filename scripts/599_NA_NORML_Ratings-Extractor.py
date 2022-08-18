# This is the webscraping script for National Organization for the Reform of Marijuana (NORML), sig_id=599

import requests
import pandas

from bs4 import BeautifulSoup

main_page = "https://vote.norml.org/"
main_pagesource = requests.get(main_page).content
main_soup = BeautifulSoup(main_pagesource,'html.parser')

states = [li.find('a')['href'] for li in main_soup.find('div', {'id':'states-container'}).find_all('li')]

records = []
dupechecks = []

for state in states:

    state_page = main_page + state
    state_pagesource = requests.get(state_page).content
    state_soup = BeautifulSoup(state_pagesource,'html.parser')
    state_code = state.split('/')[-1]

    races = state_soup.find_all('div', {'class':'race-container'})

    print(state_code)

    collected_count = 0
    inc_count = 0
    can_count = 0

    for race in races:

        race_title = race.find('div', {'class':'race-title'}).text.strip()
        candidates = race.find_all('div', {'class':'candidate-inner'})

        for candidate in candidates:

            score = candidate.find('span', {'class':'candidate-score'}).text.strip()
            name = candidate.find('span', {'class':'candidate-name'}).text.strip()
            candidate_type = 'candidate' if "Race for" in  race_title else 'incumbent'

            if "President" in race_title:
                state_id = 'NA'
            else:
                state_id = state_code

            record = {'name':name, 'score':score, 'office-district':race_title.replace("Race for ", ''), 'state':state_id, 'type':candidate_type}

            dupecheck = {'name':name, 'score':score, 'state':state_id}

            if dupecheck not in dupechecks:
                records.append(record)
                dupechecks.append(dupecheck)
                collected_count+=1

                if candidate_type == 'incumbent':
                    inc_count += 1
                elif candidate_type == 'candidate':
                    can_count += 1

    print("Incumbents:",round(inc_count/collected_count*100))
    print("Candidate:",round(can_count/collected_count*100))

df = pandas.DataFrame.from_records(records)
df.to_csv('2020_NA_NORML_Scorecard-Extract.csv')
