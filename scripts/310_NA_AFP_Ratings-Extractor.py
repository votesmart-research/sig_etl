# This is the webscraping script for Americans for Prosperity (AFP), sig_id=310

import pandas

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup
from tqdm import tqdm


URL = "https://americansforprosperity.org/national-scorecard/"


def extract(driver):
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    afp_id = driver.current_url.strip('/').split('/')[-1]
    name = soup.find('div', {'class': 'legislator-name'})
    info = soup.find('div', {'class': 'legislator-sub-head'})
    score_containers = soup.find_all('p', {'class': 'legislator-detail-score'})

    score_headers = [p.strong.text.strip() for p in score_containers]
    scores = [p.span.text.strip() for p in score_containers]

    with open(f'_NA_AFP_Ratings_{afp_id}.html', 'w') as f:
        f.write(soup.prettify())

    return {'afp_id': afp_id,
            'name': name.text.strip() if name else None,
            'info': info.text.strip() if info else None} | dict(zip(score_headers, scores))


def main():
    chrome_service = Service('chromedriver')
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('incognito')

    driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    driver.get(URL)

    while True:
        try:
            pagination = driver.find_element(By.XPATH, "//div[@class='pagination pure-u-md-1 pure-u-lg-3-4']")
            pagination.click()

        except NoSuchElementException:
            break
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    candidate_urls = [card.a['href'] for card in soup.find_all('div', {'class': 'card'})]

    records = []

    for url in tqdm(candidate_urls):
        driver.get(URL + url)
        records.append(extract(driver))

    df = pandas.DataFrame.from_records(records)
    df.to_csv('_NA_AFP_Ratings-Extract.csv', index=False)


if __name__ == '__main__':
    main()