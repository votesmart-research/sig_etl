# This is the webscraping script for The John Birch Society (JBS), sig_id=1627

from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import pandas
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from bs4 import BeautifulSoup
from tqdm import tqdm


URL = "https://thenewamerican.com/freedom-index/legislator/"


def extract_cards(page_source):

    soup = BeautifulSoup(page_source, "html.parser")
    cards = soup.find_all("div", {"class": "legislator-card"})

    for card in cards:
        name = card.find("div", {"class": "legislator-card-title"})
        office = card.find("div", {"class": "legislator-card-chamber"})
        info = card.find_all("div", {"class": "legislator-card-overview"})
        extracted_info = {
            div.small.get_text(strip=True): div.div.get_text(strip=True) for div in info
        }

        a = card.find("a")
        jbs_id = urlparse(a["href"] if a else None).path

        yield {
            "jbs_id": jbs_id.strip("/").rpartition("/")[-1] if jbs_id else None,
            "name": name.get_text(strip=True),
            "office": office.get_text(strip=True),
            "url": a["href"] if a else None,
        } | extracted_info


def extract(page_source):

    soup = BeautifulSoup(page_source, "html.parser")
    table = soup.find(string="Constitutional Votes").parent.next_sibling.next_sibling

    scores = [th.get_text(strip=True) for th in table.tbody.find_all("th")]
    session = [td.span.get_text(strip=True) for td in table.tbody.find_all("td")]

    return dict(zip(session, scores))


def extract_files(files: list):

    first_file = files[-1]

    with open(first_file, "r") as f:
        cards = list(extract_cards(f.read()))
    print(cards)
    extracted = []

    for c, file in zip(cards, files[:-1]):
        with open(file, "r") as f:
            extracted.append(c | extract(f.read()))

    return extracted


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

    # if html_path:
    #     html_files = filter(
    #         lambda f: f.name.endswith(".html"),
    #         (export_path / html_path).iterdir(),
    #     )
    #     records_extracted = extract_files(
    #         sorted(html_files, key=lambda x: x.stat().st_ctime)
    #     )
    #     return records_extracted

    chrome_service = Service()
    chrome_options = Options()
    chrome_options.add_argument("incognito")
    chrome_options.add_argument("headless")
    chrome_driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    chrome_driver.get(URL)

    ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

    WebDriverWait(chrome_driver, 15).until(
        EC.visibility_of_all_elements_located(
            (By.XPATH, "//div[@class='card legislator-card']")
        )
    )

    extracted = list(extract_cards(chrome_driver.page_source))

    for record in tqdm(extracted):
        chrome_driver.get(record["url"])
        record.pop("url")
        
        record.update(extract(chrome_driver.page_source))

        save_html(
            chrome_driver.page_source,
            export_path / "HTML_FILES",
            filename,
        )

    records_extracted = dict(enumerate(extracted))
    return records_extracted
