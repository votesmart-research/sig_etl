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
from selenium.common.exceptions import TimeoutException

from tqdm import tqdm


URL = "https://www.peaceaction.org/know-the-score/"


def extract(page_source, **additional_info):

    soup = BeautifulSoup(page_source, "html.parser")
    results = soup.select(".legislator-state-results .legislator-result")

    extracted = []

    for result in results:
        info = result.select_one("h3.legislator-name")
        score = result.select_one(".score")

        extracted.append(
            {
                "info": info.get_text(strip=True) if info else None,
                "score": score.get_text(strip=True) if score else None,
            }
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


def click_and_check(chrome_driver, map_path, prev_results):
    actions = ActionChains(chrome_driver)

    chrome_driver.execute_script(
        """
        btn = document.querySelector("#legislator-results-scroll-top")
        btn.click()
        """
    )
    time.sleep(0.75)

    actions.move_to_element(map_path).click().perform()
    time.sleep(2)

    try:
        state_results = WebDriverWait(chrome_driver, 10).until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, ".legislator-state-results")
            )
        )
    except TimeoutException:
        return None

    if state_results == prev_results:
        return None

    return state_results


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
    chrome_driver.set_window_size(1920, 1080)

    chrome_driver.get(URL)

    time.sleep(3)

    WebDriverWait(chrome_driver, 10).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "#legislator-map"))
    )

    # close overlay
    ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

    paths = chrome_driver.find_elements(By.CSS_SELECTOR, "#legislator-map path")

    old_state_results = None
    extracted = []
    not_extracted = []

    p_bar_initial = tqdm(total=len(paths))

    for path in paths:
        path_id = path.get_attribute("id")
        state_id = path_id.split("_")[-1].upper()

        p_bar_initial.desc = state_id

        state_results = click_and_check(chrome_driver, path, old_state_results)
        time.sleep(1.5)

        if state_results is None:
            not_extracted.append(path)
            print("State not Extracted: ", state_id)
            continue

        save_html(
            chrome_driver.page_source,
            export_path / "HTML_FILES",
            filename,
            state_id,
        )
        extracted += extract(chrome_driver.page_source)
        old_state_results = state_results
        p_bar_initial.update(1)

    p_bar_second = tqdm(total=len(extracted))

    for path in not_extracted:
        path_id = path.get_attribute("id")
        state_id = path_id.split("_")[-1].upper()

        p_bar_second.desc = state_id

        state_results = click_and_check(chrome_driver, path, old_state_results)
        time.sleep(1.5)

        if state_results is None:
            print("State not Extracted: ", state_id)
            continue

        save_html(
            chrome_driver.page_source,
            export_path / "HTML_FILES",
            filename,
            state_id,
        )
        extracted += extract(chrome_driver.page_source)
        old_state_results = state_results
        p_bar_second.update(1)


    extracted = extract(chrome_driver.page_source)
    records_extracted = dict(enumerate(extracted))

    return records_extracted
