# This is the webscraping script for American Energy Alliance (AEA), sig_id=2526

import time
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select


URL = "https://www.americanenergyalliance.org/american-energy-scorecard/?spage=overall"


def extract(page_source, **additional_info):

    soup = BeautifulSoup(page_source, "html.parser")
    table = soup.find("table", {"id": "overall-members-table"})

    headers = [th.get_text(strip=True) for th in table.thead.find_all("th")]
    rows = [tr.find_all("td") for tr in table.tbody.find_all("tr")]

    def get_text(x):
        return x.get_text(strip=True)

    return [dict(zip(headers, map(get_text, row))) | additional_info for row in rows]


def extract_files(files: list):

    extracted = []

    for file in files:

        with open(file, "r") as f:
            extracted += extract(f.read())

    records_extracted = dict(enumerate(extracted))

    return records_extracted


def save_html(
    page_source,
    filepath: Path,
    filename: str,
    *additional_info,
):

    filepath.mkdir(exist_ok=True)

    soup = BeautifulSoup(page_source, "html.parser")
    timestamp = datetime.strftime(datetime.now(), "%Y-%m-%d-%H%M%S-%f")

    with open(
        filepath
        / (
            f"{filename}_{'-'.join(map(str, additional_info))}"
            f"{'-' if additional_info else ''}{timestamp}.html"
        ),
        "w",
    ) as f:
        f.write(str(soup))


def main(filename: str, export_path: Path, html_path: Path = None):

    if html_path:
        html_files = filter(
            lambda f: f.name.endswith(".html"),
            (export_path / html_path).iterdir(),
        )
        records_extracted = extract_files(
            sorted(html_files, key=lambda x: x.stat().st_ctime)
        )
        return records_extracted

    chrome_service = Service()
    chrome_options = Options()
    chrome_options.add_argument("incognito")
    chrome_options.add_argument("headless")
    chrome_driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    chrome_driver.get(URL)

    select_rows = Select(chrome_driver.find_element(
        By.CSS_SELECTOR, "select[name='overall-members-table_length']"
    ))
    select_rows.select_by_value('100')
    
    time.sleep(3)

    extracted = []

    while True:
        time.sleep(2)
        next_button, current_page = chrome_driver.execute_script(
            """
            paginator = document.querySelector('#overall-members-table_paginate');
            currentPage = paginator.querySelector('.paginate_button.current').text;
            nextButton = paginator.querySelector('.paginate_button.next');

            if (!nextButton.classList.contains('disabled')){
                return [nextButton, currentPage];
            }
            else {
                return [null, currentPage];
            }                
            """
        )
        extracted += extract(chrome_driver.page_source)

        save_html(
            chrome_driver.page_source,
            export_path / "HTML_FILES",
            filename + "_" + current_page,
        )

        if next_button:
            next_button.click()
        else:
            break

    records_extracted = dict(enumerate(extracted))
    return records_extracted
