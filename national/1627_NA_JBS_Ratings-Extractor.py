# This is the webscraping script for The John Birch Society (JBS), sig_id=1627

import os
import pandas
import requests
import sys

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
from tqdm import tqdm
from datetime import datetime


MAIN_URL = "https://thenewamerican.com/freedom-index/legislator/"



def extract_cards(driver):

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    cards = soup.find_all('div', {'class':'legislator-card'})

    records = []

    for card in cards:
        name = card.find('div', {'class': 'legislator-card-title'}).text
        office = card.find('div', {'class':'legislator-card-chamber'}).text
        info = card.find_all('div', {'class': 'legislator-card-overview'})
        extracted_info = {div.small.text: div.div.text for div in info}
        url = card.a['href']
        jbs_id = url.strip('/').split('/')[-1]

        records.append({'jbs_id': jbs_id,'name': name, 'office': office, 'url': url} | extracted_info)

    return records


def extract_cpage(response):

    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find(text="Constitutional Votes").parent.next_sibling.next_sibling

    scores = [th.text.strip() for th in table.tbody.find_all('th')]
    session = [td.span.text.strip() for td in table.tbody.find_all('td')]

    return dict(zip(session, scores))


def download_page(response):

    soup = BeautifulSoup(response.text, 'html.parser')
    jbs_id = response.url.strip('/').split('/')[-1]

    if not os.path.isdir(f"{EXPORTDIR}/HTML_FILES"):
        os.mkdir(f"{EXPORTDIR}/HTML_FILES")

    with open(f"{EXPORTDIR}/HTML_FILES/_NA_JBS_Ratings_{jbs_id}.html", 'w') as f:
        f.write(soup.prettify())


def main():
    chrome_service = Service('chromedriver')
    chrome_options = webdriver.ChromeOptions()

    chrome_options.add_argument('incognito')
    chrome_options.add_argument('headless')

    driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    driver.get(MAIN_URL)

    records = extract_cards(driver)

    driver.quit()

    for record in tqdm(records):
        response = requests.get(record['url'])
        record.pop('url')
        record.update(extract_cpage(response))

        download_page(response)

    df = pandas.DataFrame.from_records(records)
    df.to_csv(f"{EXPORTDIR}/_NA_JBS_Ratings-Extract_{datetime.now().strftime('%Y-%m-%d')}.csv", index=False)


if __name__ == '__main__':
    _, EXPORTDIR = sys.argv
    main()