# This is the webscraping script for Heritage Action for America, sig_id=2061

import pandas
import os

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
from tqdm import tqdm


URL = "https://heritageaction.com/scorecard/members"
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))


def extract(soup):
    headers = [th.text.strip() for th in soup.table.find_all('th')]
    rows = soup.table.tbody.find_all('tr')
    records = []

    for row in rows:
        columns = row.find_all('td')
        info = [td.text.strip() for td in columns[:3]]
        party = columns[3].use['xlink:href'].split('#')[-1] if columns[3].use else None
        score = columns[4].text.strip()

        records.append(dict(zip(headers, info + [party, score])))

    return records


def extract_candidate(driver):

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    heritage_id = driver.current_url.split('/')[-2]

    name = soup.find('h2', {'class': 'text-2xl'})
    info = soup.find_all('span', {'class':'uppercase'})
    scores = soup.find_all('div', {'class': 'member-stats__item'})
    scores_text = {score.span.text.strip(): score.div.text.strip() for score in scores[:2]}
    state_district = info[1].text.strip().split('\n') if len(info) > 1 else []
    state = state_district[0] if state_district else ""
    district = state_district[1] if len(state_district) > 1 else ""

    record = {'heritage_id': heritage_id,
              'name': name.text.strip() if name else None,
              'party': info[0].text.strip() if info else None,
              'state': state.strip(),
              'district': district.strip()} | scores_text   

    return record


def download_page(driver):

    if not os.path.isdir(f"{SCRIPT_DIR}/Ratings"):
        os.mkdir(f"{SCRIPT_DIR}/Ratings")

    session = driver.current_url.split('/')[-1]
    candidate_id = driver.current_url.split('/')[-2]
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    with open(f"{SCRIPT_DIR}/Ratings/{session}_Ratings_{candidate_id}.html", 'w') as f:
        f.write(soup.prettify())


def main():
    chrome_service = Service('chromedriver')
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('incognito')
    chrome_options.add_argument('headless')


    driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    driver.get("https://heritageaction.com/scorecard/members")
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    candidate_urls = [tr.a['href'] for tr in soup.tbody.find_all('tr')]
    # records = extract(soup)

    records = []

    for url in tqdm(candidate_urls):

        driver.get(f"https://heritageaction.com{url}")
        records.append(extract_candidate(driver))
        download_page(driver)

    df = pandas.DataFrame.from_records(records)
    df.to_csv('_NA_Heritage_Ratings-Extract.csv', index=False)


if __name__ == '__main__':
    main()