# This is the webscraping script for Independent Petroleum Association of America (IPAA), sig_id=2439

import os
import pandas
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
from tqdm import tqdm


MAIN_URL = "https://ipaagrassroots.org"
MAP_URL = "/voting-records-map"
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
CHROMEDRIVER_PATH = os.path.abspath(SCRIPT_DIR + '/chromedriver')


def extract_states(driver):

    states = driver.find_elements(By.XPATH, "//select[@name='state']/option")
    state_urls = []

    for state in tqdm(states[1:]):
        state.click()
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        state_urls.append(soup.find('div', {'class': 'state_info'}).a['href'])

    return state_urls


def extract_officials_list(driver):

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    block_element = soup.find('div', {'class':'text-wrapper'})
    url_elements = block_element.find_all('a') if block_element else []

    return list(map(lambda a: a['href'], url_elements))


def extract_candidate(soup, candidate_id):

    name = soup.find('h1', {'class': 'candidate-name'})
    office = soup.find('h2', {'class': 'candidate-office'})
    lifetime_score = soup.find('p', {'class':'score'})
    party = soup.find('p', {'ng-if': 'officials.currentOfficial.personal.party'})
    district_office = soup.find('div', {'ng-switch': 'officials.currentOfficial.position.title'})
    district = district_office.p if district_office else None

    if party:
        if party.span:
            party.span.decompose()

    if district_office:
        if district_office.span:
            district_office.span.decompose()

    def get_voting_records(soup):

        legislation_title = soup.find('li', {'class': 'legislation-title'})
        session_wrapper = legislation_title.find_next_sibling() if legislation_title else None
        voting_record = session_wrapper.find('div', {'class': 'panel'}) if session_wrapper else None

        if voting_record:
            sessions = list(map(lambda h4: h4.text.strip() if h4 else None, voting_record.find_all('h4')))
            scores = list(map(lambda div: div.span.text.strip() if div else None, voting_record.find_all('div', {'class':'aligned-score'})))
            return dict(zip(sessions, scores))

        else:
            return {}

    record = {'ipaa_candidate_id': candidate_id,
              'name': name.text.strip() if name else None,
              'office': office.text.strip() if office else None,
              'party': party.text.strip() if party else None,
              'district': district.text.strip() if district else None,
              'lifetime_score': lifetime_score.text.strip() if lifetime_score else None}

    return record | get_voting_records(soup)


def file_to_soup(file):
    with open(file, 'r') as f:
        return BeautifulSoup(f.read(), 'html.parser')


def download_page(driver):

    if not os.path.isdir(f"{SCRIPT_DIR}/Ratings"):
        os.mkdir(f"{SCRIPT_DIR}/Ratings")

    candidate_id = driver.current_url.split('/')[-1]
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    with open(f"{SCRIPT_DIR}/Ratings/Ratings_{candidate_id}.html", 'w') as f:
        f.write(soup.prettify())


def main():    
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('incognito')
    chrome_options.add_argument('headless')

    chrome_service = Service('chromedriver')
    driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    driver.get(MAIN_URL +  MAP_URL)
    
    try:
        map_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'us_map21')))

    except TimeoutException:
        print("Map element not found. Quitting...")
        exit()

    state_urls = extract_states(driver)

    officials_urls = []

    for url in tqdm(state_urls):

        driver.get(f"{MAIN_URL}/{url}")

        try:
            officials_list = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//div[@class='text-wrapper ng-scope ng-isolate-scope']")))

        except TimeoutException:
            continue

        officials_urls += extract_officials_list(driver)

    records = []
    rating_files = [d.split('_')[-1].strip('.html') for d in os.listdir(f"{SCRIPT_DIR}/Ratings") if d.startswith('Ratings')]

    for url in tqdm(officials_urls):

        ipaa_candidate_id = url.split('/')[-1]
    
        if ipaa_candidate_id in rating_files:

            soup = file_to_soup(f'Ratings/Ratings_{ipaa_candidate_id}.html')
            records.append(extract_candidate(soup, ipaa_candidate_id))

        else:
            driver.get(f"{MAIN_URL}/{url}")

            try:
                officials_name = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//h1[@class='title candidate-name ng-binding']")))
            
            except TimeoutException:
                continue

            soup = BeautifulSoup(driver.page_source, 'html.parser')

            records.append(extract_candidate(soup, ipaa_candidate_id))
            download_page(driver)

    df = pandas.DataFrame.from_records(records)
    df.to_csv('_NA_IPAA_Ratings-Extract.csv', index=False)

    driver.quit()


if __name__ == "__main__":
    main()