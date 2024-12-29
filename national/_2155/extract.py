from datetime import datetime
from pathlib import Path
import time
from collections import defaultdict

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    ElementNotInteractableException,
)
from tqdm import tqdm


URL = "https://www.termlimits.com/legislators/"


def extract(page_source, **additional_info):

    soup = BeautifulSoup(page_source, "html.parser")
    cards = soup.select("div.federal > div.row")

    extracted = []

    for card in cards:
        name = card.select_one("h1.ll-title")
        grade = card.select_one("span.ll-grade-img")

        extracted.append(
            {
                "name": name.get_text(strip=True) if name else None,
                "grade": grade.get_text(strip=True) if grade else None,
            }
            | additional_info
        )

    return extracted


def extract_files(files: list[Path]):

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


def show_legislators(driver: webdriver.Chrome, zip_code):

    address_input = driver.find_element(By.CSS_SELECTOR, "input#ll-address-input")

    try:
        address_input.clear()
        address_input.send_keys(zip_code)
        address_input.send_keys(Keys.ENTER)
        time.sleep(1)
        try:
            _ = address_input.tag_name
            return False
        except StaleElementReferenceException:
            return True

    except ElementNotInteractableException:
        driver.back()
        address_input = driver.find_element(By.CSS_SELECTOR, "input#ll-address-input")
        address_input.clear()
        address_input.send_keys(zip_code)
        address_input.send_keys(Keys.ENTER)
        time.sleep(1)
        try:
            _ = address_input.tag_name
            return False
        except StaleElementReferenceException:
            return True

    except StaleElementReferenceException:
        time.sleep(5)


def main(
    filename: str,
    export_path: Path,
    zipcode_records: list[dict],
    html_path: Path = None,
):

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

    unique_states = defaultdict(set)
    repsens_by_state = {}

    for record in zipcode_records:
        state_id = record.pop("state_id")
        repsens = int(record.get("reps")) + int(record.get("sens"))

        if repsens > 0:
            unique_states[state_id].add(record["zip"])

        if state_id not in repsens_by_state and repsens > 0:
            repsens_by_state[state_id] = repsens

    # close overlay
    ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

    extracted = defaultdict(list)

    chrome_driver.get(URL)

    p_bar = tqdm(total=len(unique_states), desc="Extracting states...")

    for state_id in unique_states:

        repsens = repsens_by_state.get(state_id)
        zip_codes = sorted(unique_states.get(state_id))

        i = round(len(zip_codes) / repsens) + 1

        start = 0
        end = i

        sliced_zips = []

        while start < len(zip_codes) - 1:
            sliced_zips.append(zip_codes[start:end])

            start = end
            end += i

        state_p_bar = tqdm(total=len(zip_codes), desc=f"Extracting {state_id} ({i})...")

        # Stop when it has too many iterations.
        exhaust_counter = 0

        while True:

            if len(extracted[state_id]) >= repsens:
                break

            for sliced_zip in sliced_zips:

                if len(sliced_zip) > 0:
                    current_zip = sliced_zip.pop()
                    state_p_bar.update(1)
                    p_bar.refresh()

                    obtained = show_legislators(chrome_driver, current_zip)
                    time.sleep(1)

                    if obtained is True:
                        found_counter = 0

                        for e in extract(chrome_driver.page_source, state_id=state_id):
                            if e not in extracted[state_id]:
                                found_counter += 1
                                extracted[state_id].append(e)

                        if found_counter == 0:
                            exhaust_counter += 1
                        else:
                            save_html(
                                chrome_driver.page_source,
                                export_path / "HTML_FILES",
                                filename,
                                state_id,
                                current_zip,
                            )
                            exhaust_counter = 0

                    if exhaust_counter > i:
                        break

                    if len(extracted[state_id]) >= repsens:
                        break

            if exhaust_counter > i:
                break

            if not any(sliced_zips):
                break

        p_bar.update(1)

    _extracted = []
    for state_id, record in extracted.items():
        _extracted += record

    records_extracted = dict(enumerate(_extracted))

    return records_extracted
