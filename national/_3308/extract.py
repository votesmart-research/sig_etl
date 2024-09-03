import re
import time
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
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from tqdm import tqdm

URL = "https://climatecabinet.org/climate-scores"


def extract_card(page_source, **additional_info):

    soup = BeautifulSoup(page_source, "html.parser")
    card = soup.find("div", {"data-testid": "spotlight--0"})

    office = card.find("div", {"class": "_retool-container-spotlight_office"})
    party = card.find("div", {"class": "_retool-container-spotlight_party"})

    return {
        "Chamber_dist": office.get_text(strip=True) if office else None,
        "Party_long": party.get_text(strip=True) if party else None,
    } | additional_info


def extract_table(page_source, **additional_info):

    soup = BeautifulSoup(page_source, "html.parser")

    header_container = soup.find("div", {"role": "rowheader"})
    row_container = soup.find("ol")

    header_divs = [
        div for div in header_container.find_all("div", {"role": "gridcell"})
    ]
    row_lis = row_container.find_all("li")

    headers = []
    for header in header_divs:
        col = header.find(
            lambda tag: tag.name == "span"
            and tag.has_attr("data-testid")
            and "HeaderCellContents" in tag.get("data-testid")
        )

        headers.append(col.get_text(strip=True))

    extracted = {}

    for row in row_lis:
        row_index = row.get("data-item-index")
        columns = [
            col.get_text(strip=True)
            for col in row.find_all("div", {"role": "gridcell"})
        ]
        extracted[row_index] = dict(zip(headers, columns)) | additional_info

    return extracted


def extract_files(files: list[Path]):

    extracted = []

    for file in files:

        with open(file, "r") as f:
            extracted += extract_card(f.read())

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


def js_click(chrome_driver, element):
    chrome_driver.execute_script(
        """
        arguments[0].click()
        """,
        element,
    )


def scroll_states(driver, func=None):
    state_button_script = """
        return document.querySelector("button[data-testid*='state_select--0']")
        """

    state_container_script = """
        return document.querySelector("div[data-testid='SelectListBox']")
    """

    states_script = (
        """return arguments[0].querySelectorAll("div[data-testid*='ListBoxItem']")"""
    )

    progress_bar = tqdm(total=1, desc="Commencing...")
    selected_states = []
    state_button = driver.execute_script(state_button_script)

    extracted = []

    while True:
        js_click(driver, state_button)
        time.sleep(1)

        state_container = driver.execute_script(state_container_script)
        states = driver.execute_script(states_script, state_container)
        state_texts = {s.text for s in states}

        progress_bar.total = len(states)

        if not state_texts.difference(set(selected_states)):
            break

        for state in states:
            s_text = state.text
            if not s_text in selected_states:
                js_click(driver, state)
                time.sleep(2)

                selected_states.append(s_text)
                progress_bar.set_description(f"Extracing {s_text}...")

                if func:
                    extracted += func(driver, s_text)
                    progress_bar.update(1)

                break
            else:
                continue

        if driver.execute_script(state_container_script):
            js_click(driver, state_button)

    return extracted


def scroll_candidates(driver, state, save_html=None):

    table_script = """
        return document.getElementById("scores--0")
        """

    table_footer_script = """
        return arguments[0].querySelector("div[data-is-footer=true]")
    """
    table_selected_row_script = """
        return arguments[0].querySelector("ol > li[aria-selected=true]")
    """

    table_scroll_script = """
        event = new KeyboardEvent('keydown', {
            key: 'ArrowDown',
            code: 'ArrowDown'
        });
        arguments[0].dispatchEvent(event)                    
        """

    table = driver.execute_script(table_script)
    table_footer = driver.execute_script(table_footer_script, table)

    footer_text = re.findall("\\d+", table_footer.text if table_footer else "")
    total_results = int(footer_text.pop()) if footer_text else 0

    progress_bar_candidates = tqdm(total=total_results, desc="Extracting Candidates...")

    extracted = extract_table(table.get_attribute("outerHTML"))
    extracted_cards = {"0": extract_card(driver.page_source)}

    if save_html:
        save_html(driver, state)

    selected_rows = []

    progress_bar_candidates.update(1)

    while True:
        driver.execute_script(table_scroll_script, table)
        time.sleep(1)

        currently_selected = driver.execute_script(table_selected_row_script, table)
        row_num = currently_selected.get_attribute("data-item-index")

        if row_num in selected_rows:
            break

        if save_html:
            save_html(driver, state)

        extracted.update(extract_table(table.get_attribute("outerHTML"), state=state))
        extracted_cards.update({row_num: extract_card(driver.page_source)})

        selected_rows.append(row_num)
        progress_bar_candidates.update(1)

    for i, card_record in extracted_cards.items():
        if i in extracted:
            extracted[i].update(card_record)

    return list(extracted.values())


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
    # chrome_options.add_argument("headless")
    chrome_driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    chrome_driver.get(URL)

    iframe_script = (
        """return document.querySelector("iframe[src*='climatecabinet.retool.com']")"""
    )

    # close overlay
    ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

    # iframe = wait_for_js_script(chrome_driver, iframe_script, elname='iframe')

    time.sleep(5)

    iframe = chrome_driver.execute_script(iframe_script)
    chrome_driver.switch_to.frame(iframe)

    extracted = scroll_states(
        chrome_driver,
        lambda driver, state: scroll_candidates(
            driver,
            state,
            lambda driver, state: save_html(
                driver.page_source, export_path / "HTML_FILES", filename, state
            ),
        ),
    )

    return dict(enumerate(extracted))
    # return {0: []}
