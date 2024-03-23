from datetime import datetime
from pathlib import Path
from itertools import chain
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from tqdm import tqdm


URL = "https://vote.norml.org/"


def extract(page_source, **additional_info) -> list:

    soup = BeautifulSoup(page_source, "html.parser")
    race_containers = soup.find_all(class_="race-container")
    state = soup.find(class_="big-title").get_text(strip=True)
    state_text = state.replace(" Guide", "")

    def extract_container(race_container):
        office = race_container.find(class_="race-title")
        endorsed_containers = race_container.find_all(class_="endorsed-container")

        for ec in endorsed_containers:
            name = ec.find(class_="candidate-name")
            score = ec.find(class_="candidate-score")

            yield {
                "name": name.get_text(strip=True, separator=" "),
                "score": score.get_text(strip=True, separator=" "),
                "office": office.get_text(strip=True, separator=" "),
                "state": state_text,
            } | additional_info

    extracted = []
    for rc in race_containers:
        extracted += list(extract_container(rc))

    return extracted


def extract_files(files: list):

    extracted = []

    for file in files:

        with open(file, "r") as f:
            extracted += extract(f.read())

    return {
        "candidates": list(
            filter(lambda record: record["office"].startswith("Race for"), extracted)
        ),
        "incumbents": list(
            filter(
                lambda record: not record["office"].startswith("Race for"), extracted
            )
        ),
    }


def get_states(page_source):
    soup = BeautifulSoup(page_source, "html.parser")
    state_links = chain(*(l.find_all("a") for l in soup.find_all(class_="state-list")))
    return {a.get_text(strip=True): urljoin(URL, a["href"]) for a in state_links}


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


def main(filename, export_path: Path, html_path: Path = None):

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

    # close overlay
    ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

    states = get_states(chrome_driver.page_source)
    p_bar = tqdm(total=len(states), desc="Extracting State")

    extracted = []

    for state, url in states.items():
        p_bar.desc = f"Extracting {state}"

        chrome_driver.get(url)
        extracted += extract(chrome_driver.page_source)
        save_html(
            chrome_driver.page_source,
            export_path / "HTML_FILES",
            filename,
            state,
        )

        p_bar.update(1)

    return {
        "candidates": dict(
            enumerate(
                filter(
                    lambda record: record["office"].startswith("Race for"),
                    extracted,
                )
            )
        ),
        "incumbents": dict(
            enumerate(
                filter(
                    lambda record: not record["office"].startswith("Race for"),
                    extracted,
                )
            )
        ),
    }
