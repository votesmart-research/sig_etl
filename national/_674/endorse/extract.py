from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException

from tqdm import tqdm

URL = "https://hslf.org/endorsements"


def extract_list(page_source, **additional_info):

    soup = BeautifulSoup(page_source, "html.parser")

    endorse_list = soup.select_one("div.endorsements-list p")

    extracted = []
    current_state = endorse_list.parent.parent.find_previous("h3")
    current_office = None
    current_info = None

    for element in endorse_list.find_all(["strong", "br"]):
        if element.name == "strong":
            # Update the current office
            current_office = element.get_text(strip=True)
        elif element.name == "br":
            # Try to find the next text element for this info
            next_element = element.next_sibling
            if next_element and isinstance(next_element, str) and next_element.strip():
                # Strip and store the information with the current office
                current_info = next_element.strip()
                extracted.append(
                    {
                        "office": current_office,
                        "info": current_info,
                        "state": current_state.get_text(strip=True),
                    }
                )
    return extracted


def extract_files(files: list[Path]):

    extracted = []

    for file in files:

        with open(file, "r") as f:
            extracted += extract_list(f.read())

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

    # close overlay
    ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

    save_html(
        chrome_driver.page_source,
        export_path / "HTML_FILES",
        filename,
    )

    states_links = chrome_driver.find_elements(By.CSS_SELECTOR, ".card a.card-link")

    extracted = []

    for card_link in tqdm(states_links):
        chrome_driver.execute_script(
            """
            arguments[0].click()
            """,
            card_link,
        )

        WebDriverWait(chrome_driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "div.endorsements-list"))
        )
        save_html(
            chrome_driver.page_source,
            export_path / "HTML_FILES_STATES",
            filename,
        )
        extracted += extract_list(chrome_driver.page_source)

        ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

    records_extracted = dict(enumerate(extracted))

    return records_extracted
