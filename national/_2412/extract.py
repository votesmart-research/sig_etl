import re
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup


URL = "https://libertyscore.conservativereview.com/"


def extract(page_source):

    soup = BeautifulSoup(page_source, "html.parser")

    table = soup.find("table", {"id": "repsTable"})
    headers = [th.div.text for th in table.thead.find_all("th")]

    rows = [tr.find_all("td") for tr in table.tbody.find_all("tr")]

    def get_text(x):
        return x.text.strip()

    extracted = []

    for row in rows:
        info_1 = dict(zip(headers[:2], map(get_text, row[:2])))
        party = re.sub(r".svg|.png", "", row[2].img["src"].split("/")[-1])
        info_2 = dict(zip(headers[3:], map(get_text, row[3:])))
        extracted.append(info_1 | {"party": party} | info_2)

    return extracted


def extract_files(files: list):

    extracted = []

    for file in files:
        with open(file, "r") as f:
            extracted += extract(f.read())


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

    chrome_service = Service()
    chrome_options = Options()
    chrome_options.add_argument("incognito")
    chrome_options.add_argument("headless")
    chrome_driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    chrome_driver.get(URL)

    WebDriverWait(chrome_driver, 10).until(
        EC.presence_of_element_located((By.ID, "repsTable"))
    )

    # close overlay
    ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

    save_html(
        chrome_driver.page_source,
        export_path / "HTML_FILES",
        filename,
    )
    extracted = []

    while True:
        
        next_button = chrome_driver.execute_script(
            """
            return document.querySelector("button[aria-label='Go to next page']")
            """
        )

        if next_button:
            next_button.click()
            extracted += extract(chrome_driver.page_source)

            save_html(
                chrome_driver.page_source,
                export_path / "HTML_FILES",
                filename,
            )
        else:
            break
    
    records_extracted = dict(enumerate(extracted))
    return records_extracted
