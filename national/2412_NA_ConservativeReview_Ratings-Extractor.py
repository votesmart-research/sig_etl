# This is the webscraping script for Conservative Review, sig_id=2412

import os
import time
import pandas
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup
from datetime import datetime


def close_overlay(d):
    try:
        el_1 = d.find_element(By.ID, "sailthru-overlay-container")
        el_2 = el_1.find_element(By.XPATH, "//button[@class='sailthru-overlay-close']")
        el_2.click()
        print('Closed Overlay')
    except:
        d.quit()
        print("OVERLAY NOT FOUND!")


def get_paginator(d):
    container = d.find_element(By.XPATH, "//ul[@class='pagination pagination b-pagination']")
    active = container.find_element(By.XPATH, "//li[@class='page-item active']").text

    lis = container.find_elements(By.TAG_NAME, "li")

    try:
        go_next = lis[-2].find_element(By.TAG_NAME, "button")
        return go_next, active
    
    except NoSuchElementException:
        return False, active
    

def get_page_soup(d):
    soup = BeautifulSoup(d.page_source, 'html.parser')
    return soup


def soup_to_html(soup, filename):
    pretty_soup = soup.prettify()
    with open(filename + '.html', 'w') as f:
        f.write(pretty_soup)


def extract(soup):

    tbody = soup.find('table', id='repsTable').find('tbody')
    rows = tbody.find_all('tr')

    records = []

    for row in rows:

        cols = row.find_all('td')
        info = {'Name': None, 'Score': None, 'Party': None, 'State': None, 'Office': None}

        info['Name'] = ' '.join(cols[0].text.strip().split(' ')[1:]).strip()
        info['Office'] = cols[0].find('strong').text.strip()
        info['Score'] = cols[1].text.strip()
        info['Party'] = cols[2].find('img')['src'].split('/')[-1].replace('.svg', '').replace('.png', '')
        info['State'] = cols[3].text.strip()

        records.append(info)

    return records


def main():

    chrome_service = Service(os.getcwd()+'/chromedriver')
    chrome_options = webdriver.ChromeOptions()
    download_path = "."

    appState = {"recentDestinations": [{"id": "Save as PDF", 
                                    "origin": "local",
                                   "account": ""}],
             "selectedDestinationId": "Save as PDF", 
                           "version": 2}

    profile = {'printing.print_preview_sticky_settings.appState': json.dumps(appState),
               'savefile.default_directory': download_path}

    # browse in incognito (private) mode
    chrome_options.add_argument('--incognito')
    # allow for printing page (Ctrl+P on Windows or Cmd+P on MacOS)
    chrome_options.add_argument('--kiosk-printing')
    chrome_options.add_experimental_option('prefs', profile)


    driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
    main_url = "https://libertyscore.conservativereview.com/"


    records = []

    driver.get(main_url)
    time.sleep(7)

    # close_overlay(driver)

    go_next, active = get_paginator(driver)
    current_year = datetime.now().year

    while True:
        
        soup = get_page_soup(driver)

        current_time = datetime.now().strftime('%Y-%m-%d-%H%M%S')

        records += extract(soup)
        

        soup_to_html(soup, f'{current_year}_NA_ConservativeReview_Ratings_{active}-lifetime-{current_time}')
        time.sleep(1)

        if not go_next:
            break

        go_next.click()
        go_next, active = get_paginator(driver)

    print('Quitting Browser...')

    time.sleep(1)
    driver.quit()
    pandas.DataFrame.from_records(records).to_csv(
          f'{current_year}_NA_ConservativeReview_Ratings-Extract_lifetime.csv', index=False)

if __name__ == '__main__':
    main()
