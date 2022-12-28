
import os
import sys
import pandas

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup


URL = ""
FILENAME = ""


def extract(driver:webdriver.Chrome):
    soup = BeautifulSoup(driver.page_source, 'html.parser')


def download_page(driver:webdriver.Chrome):
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    if not os.path.isdir(HTML_FILES):
        os.mkdir(HTML_FILES)

    filename = f"{FILENAME}"

    with open(f"{HTML_FILES}/{filename}", 'w') as f:
        f.write(soup.prettify())


def main():
    chrome_service = Service('chromedriver')
    chrome_options = Options()
    chrome_options.add_argument('incognito')
    # chrome_options.add_argument('headless')

    chrome_driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    chrome_driver.get(URL)

    soup = BeautifulSoup(chrome_driver.page_source, 'html.parser')

    df = pandas.DataFrame.from_records()
    df.to_csv(f"{FILENAME}-Extract.csv", index=False)
    

if __name__ == '__main__':
    _, EXPORT_DIR = sys.argv
    HTML_FILES = f"{EXPORT_DIR}/HTML_FILES"

    main()