# This is the webscraping script for Armenian National Committee of America (ANCA), sig_id=1420

import os
import pandas
import time
import sys

from collections import defaultdict
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
from tqdm import tqdm


URL = "https://anca.org/report-card"


def driver_to_soup(driver, url, delay=0):
    driver.get(url)
    time.sleep(delay)
    return BeautifulSoup(driver.page_source, 'html.parser')


def extract_candidate_urls(soup):
    current_years = soup.find_all('div', {'class': 'grade-current-year'})

    urls = []

    for current_year in current_years:
        url_container = current_year.find_next_sibling('div')
        a = list(map(lambda a: a['href'], url_container.find_all('a'))) if url_container else []
        urls += a

    return urls


def extract_candidate_url(soup, session):

    grade = soup.find('div', {'class': 'cong-grade-single'})
    grade_container = grade.parent if grade else None
    grade_by_sessions = grade_container.parent.find_next_sibling('div') if grade_container else None

    urls = list(map(lambda a: a['href'] if a else '', grade_by_sessions.find_all('a')))
        
    for url in urls:
        url_split = url.split('-')
        url_session = url_split[-1] if url_split else None

        if session == url_session:
            return url


def extract_candidate_info(soup, url):
    url_dash_split = url.strip('/').split('-')
    url_slash_split = url.strip('/').split('/')

    grade = soup.find('div', {'class': 'cong-grade-single'})
    grade_container = grade.parent if grade else None
    info_container = grade_container.parent.find_previous_sibling('div') if grade_container else None

    name = info_container.h2 if info_container else None
    psd = info_container.h4 if info_container else None

    return {'anca_candidate_id': url_dash_split[-2] if len(url_dash_split) >= 2 else None,
            'name': name.text.strip() if name else None,
            'party-state-district': psd.text.strip() if psd else None,
            'office': url_slash_split[-2] if len(url_slash_split) >= 3 else None ,
            'candidate_url': url_slash_split[-1] if len(url_slash_split) >= 2 else None,
            'session': url_dash_split[-1] if url_dash_split else None,
            'grade': grade.text.strip() if grade else None}


def download_page(driver, session):

    if not os.path.isdir(f"{EXPORTDIR}/HTML_FILES"):
        os.mkdir(f"{EXPORTDIR}/HTML_FILES")

    url_dash_split = driver.current_url.strip('/').split('-')
    candidate_id = url_dash_split[-2] if len(url_dash_split) >=2 else None
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    with open(f"{EXPORTDIR}/HTML_FILES/{session}_Ratings_{candidate_id}.html", 'w') as f:
        f.write(soup.prettify())


def main():

    chrome_service = Service('chromedriver')
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('incognito')
    
    driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
    soup = driver_to_soup(driver, URL)
    state_options = list(map(lambda o: o['value'], soup.find('select', {'id': 'cat'}).find_all('option')))

    urls_by_state = defaultdict(list)

    for state in tqdm(state_options[1:], desc="Getting URLs..."):
        soup = driver_to_soup(driver, f"{URL}/?state={state}")
        urls_by_state[state] = extract_candidate_urls(soup)

    records = list()
    blank_records = defaultdict(str)
    urls_to_check = defaultdict(str)

    for state, urls in tqdm(urls_by_state.items(), desc="Extracting..."):
        for url in tqdm(urls, desc=state):
            soup = driver_to_soup(driver, url)
            record = extract_candidate_info(soup, url)

            if record['name']:
                records.append(record)
                download_page(driver, record['session'])

                if record['anca_candidate_id'] in blank_records.keys():
                    urls_to_check[url] = blank_records[record['anca_candidate_id']]
                    blank_records.pop(record['anca_candidate_id'])
            else:
                blank_records[record['anca_candidate_id']] = record['session']
        

    for url, session in tqdm(urls_to_check.items(), desc="Correcting Errors..."):
        
        to_go = extract_candidate_url(driver_to_soup(driver, url), session)

        if to_go:
            soup = driver_to_soup(driver, to_go)
            records.append(extract_candidate_info(soup, to_go))
            download_page(driver, session)

    df = pandas.DataFrame.from_records(records)
    df.to_csv(f'{EXPORTDIR}_NA_ANCA_Ratings-Extract.csv', index=False)


if __name__ == "__main__":
    _, EXPORTDIR = sys.argv
    main()