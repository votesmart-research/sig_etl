import time
from datetime import datetime
from pathlib import Path


import pandas
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import Select

from tqdm import tqdm


URL = "https://aflcio.org/scorecard/legislators"


def get_last_page(page_source):
    soup = BeautifulSoup(page_source, "html.parser")

    e = soup.find("li", {"class": "pager__item--last"})
    last_page_url = e.a["href"].strip("?") if e else ""
    params = [p.split("=") for p in last_page_url.split("&")] if last_page_url else []
    cleaned_params = {p: v for p, v in params} if params else {}

    return int(cleaned_params["page"]) if "page" in cleaned_params else 0


def get_current_page(page_source):
    soup = BeautifulSoup(page_source, "html.parser")

    e = soup.find("li", {"class": "pager__item is-active"})
    link = e.find('a') if e else None
    
    if link and link.span:
        link.span.decompose()
    
    return link.get_text(strip=True)


def extract(page_source, **additional_info):

    soup = BeautifulSoup(page_source, 'html.parser')
    table = soup.find('table')
    
    def extract_table(table):

        headers = [th.get_text(strip=True)
                   for th in table.thead.find_all('th')[1:]]
        rows = [tr.find_all('td')[1:] for tr in table.tbody.find_all('tr')]

        def get_text(x): return x.get_text(strip=True)

        return [dict(zip(headers, map(get_text, row))) | additional_info for row in rows]

    return extract_table(table)


def extract_files(files: list):

    extracted = []

    for file in files:

        with open(file, 'r') as f:
            extracted += extract(f.read())

    return extracted


def save_html(page_source, filepath, *additional_info):

    soup = BeautifulSoup(page_source, 'html.parser')

    filepath = Path(filepath) / 'HTML_FILES'
    filepath.mkdir(exist_ok=True)

    timestamp = datetime.strftime(datetime.now(), '%Y-%m-%d-%H%M%S-%f')

    with open(filepath / f"Ratings_{'-'.join(map(str, additional_info))}"
                         f"{'-' if additional_info else ''}{timestamp}.html", 'w') as f:
        f.write(str(soup))


def save_extract(extracted: list[dict], filepath, *additional_info):

    filepath = Path(filepath) / 'EXTRACT_FILES'
    filepath.mkdir(exist_ok=True)

    timestamp = datetime.strftime(datetime.now(), '%Y-%m-%d-%H%M%S-%f')

    df = pandas.DataFrame.from_records(extracted)
    df.to_csv(
        filepath / f"Ratings-Extract_{'-'.join(map(str, additional_info))}"
                   f"{'-' if additional_info else ''}{timestamp}.csv", index=False)


def main(export_dir, year=None):

    chrome_service = Service()
    chrome_options = Options()
    chrome_options.add_argument('incognito')
    chrome_options.add_argument('headless')
    chrome_driver = webdriver.Chrome(
        service=chrome_service, options=chrome_options)

    chrome_driver.get(URL)

    # close overlay
    ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

    if year:
        scorecard_year = chrome_driver.execute_script(
            """
            return document.querySelector('select[class^=scorecard-year]')
            """
        )
        select_year = Select(scorecard_year)
        select_year.select_by_value(year)


    office_container = chrome_driver.find_element(By.XPATH, ("//div[@class='scorecard-list-nav legislator-list-nav']"))
    offices = office_container.find_elements(By.TAG_NAME, "a")
    
    extracted = []    

    for i in range(0,len(offices)):
        chrome_driver.execute_script("arguments[0].click()", offices[i])
        time.sleep(2)
        
        p_bar = tqdm(total=get_last_page(chrome_driver.page_source), 
                                         desc=f"Extracting {offices[i].text}...")
        
        while True:
            next_button = chrome_driver.execute_script(
                """
                return document.getElementsByClassName('pager__item--next')[0]
                """
            )
            
            extracted += extract(chrome_driver.page_source, office=offices[i].text)
            save_html(chrome_driver.page_source, export_dir, offices[i].text, get_current_page(chrome_driver.page_source))
            
            if next_button:
                next_button.click()
                p_bar.update(1)
            else:
                break
            time.sleep(1)
            
        office_container = chrome_driver.find_element(By.XPATH, ("//div[@class='scorecard-list-nav legislator-list-nav']"))
        offices = office_container.find_elements(By.TAG_NAME, "a")

    return extracted


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(prog='sig_webscrape')
    parser.add_argument('-d', '--exportdir', type=Path, required=True,
                        help='file directory of where the files exports to')
    parser.add_argument('-f', '--htmldir', type=Path,
                        help='file directory of html files to read')
    
    def check_for_years(x):
        if int(x) in range(2000,2100):
            return x
        else:
            raise ValueError
    
    parser.add_argument('-y', '--year', type=check_for_years,
                        help='Check for years')

    args = parser.parse_args()
    
    if args.htmldir:
        html_files = filter(lambda f: f.name.endswith(
            '.html'), (args.exportdir / args.htmldir).iterdir())
        extracted = extract_files(
            sorted(html_files, key=lambda x: x.stat().st_ctime))
    else:
        extracted = main(args.exportdir, args.year)

    save_extract(extracted, args.exportdir)