from datetime import datetime
from pathlib import Path
import time

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

URL = "https://retiredamericans.org/2024-federal-candidate-endorsements/"


def extract(page_source, **additional_info):

    soup = BeautifulSoup(page_source, "html.parser")
    tooltips = soup.select("div.i_world_map li.google-visualization-tooltip-item")

    state = tooltips[0] if len(tooltips) > 0 else None
    candidate_list = tooltips[1] if len(tooltips) > 1 else None

    candidates = (
        candidate_list.get_text(strip=True, separator=";").split(";")
        if candidate_list
        else []
    )

    extracted = [
        {"name": c, "state": state.get_text(strip=True) if state else None}
        | additional_info
        for c in candidates
    ]

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

    time.sleep(5)

    # close overlay
    ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

    chrome_driver.execute_script(
        """
            modal = document.querySelector("div#myModalRetired")
            modal.remove()
        """
    )

    us_map = chrome_driver.find_element(By.CSS_SELECTOR, "div.i_world_map")
    map_paths = us_map.find_elements(By.CSS_SELECTOR, "g > path")

    extracted = []

    for path_el in tqdm(map_paths, desc="Hovering map..."):
        ActionChains(chrome_driver).move_to_element(path_el).perform()
        _e = extract(chrome_driver.page_source)

        not_appended = set()

        for item in _e:
            if item not in extracted:
                not_appended.add(True)
                extracted.append(item)

        if any(not_appended):
            save_html(
                chrome_driver.page_source,
                export_path / "HTML_STATE_FILES",
                filename,
            )

        time.sleep(0.15)

    records_extracted = dict(enumerate(extracted))

    return records_extracted
