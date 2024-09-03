# This is the webscraping script for Susan B. Anthony List, sig_id = 1946
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from tqdm import tqdm


URL = "https://sbaprolife.org/scorecard"
RATINGS_METHODOLOGY = {
    "sc_cross.png": "-",
    "sc_nv.png": "*",
    "sc_check.png": "+",
}


def extract(page_source):
    soup = BeautifulSoup(page_source, "html.parser")
    name = soup.select_one(".sc_name_large h1")
    info = soup.select_one(".sc_name_large p")
    grade_rating = soup.select_one(".sc_rating h2")
    votes_table = soup.select(".sc_table")

    votes_table_rows = votes_table[0].select("tbody tr")

    ratings_by_session = defaultdict(str)

    for row in votes_table_rows:
        columns = row.find_all("td")
        session = columns[0].select_one(".date_congress")

        score_img = columns[-1].find("img")
        session_text = session.get_text(strip=True) if session else None

        if score_img.has_attr("data-lazy-src"):
            score_img_src = score_img["data-lazy-src"]
        else:
            score_img_src = score_img["src"]

        vote = score_img_src.split("/")[-1:] if score_img else None
        vote_score = RATINGS_METHODOLOGY.get("".join(vote))

        if session_text is None:
            active_tab = soup.select_one("input[name=sc_tabs][checked=checked]")
            tab_label = active_tab.find_next_sibling("label")
            ratings_by_session[tab_label.get_text(strip=True)] += vote_score
        else:
            ratings_by_session[session_text] += vote_score

    return {
        "name": name.get_text(strip=True) if name else None,
        "info": info.get_text(strip=True) if name else None,
        "grade": grade_rating.get_text(strip=True) if name else None,
    } | ratings_by_session


def extract_files(files: list[Path]):

    extracted = []

    for file in files:

        with open(file, "r") as f:
            extracted.append(extract(f.read()))

    records_extracted = dict(enumerate(extracted))

    return records_extracted


def get_candidate_urls(page_source):
    soup = BeautifulSoup(page_source, "html.parser")

    senate_links = soup.select("#sc_dt_sen strong a")
    house_links = soup.select("#sc_dt_house strong a")

    for a in senate_links + house_links:
        yield a["href"]


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
    chrome_driver = webdriver.Chrome(options=chrome_options, service=chrome_service)
    chrome_driver.get(URL)

    sen_entries_info = chrome_driver.find_element(By.ID, "sc_dt_sen_info")
    house_entries_info = chrome_driver.find_element(By.ID, "sc_dt_house_info")

    sen_info_items = list(re.finditer(r"\d+", sen_entries_info.text))
    house_info_items = list(re.finditer(r"\d+", house_entries_info.text))

    sen_max_entries = sen_info_items[-1].group(0) if len(sen_info_items) > 2 else 1000
    house_max_entries = (
        house_info_items[-1].group(0) if len(house_info_items) > 2 else 1000
    )

    senate_select = Select(
        chrome_driver.find_element(By.XPATH, "//select[@name='sc_dt_sen_length']")
    )

    house_select = Select(
        chrome_driver.find_element(By.XPATH, "//select[@name='sc_dt_house_length']")
    )

    for sel, ent in zip(
        (senate_select, house_select),
        (sen_max_entries, house_max_entries),
    ):
        chrome_driver.execute_script(
            """
            arguments[0].value = arguments[1]
            arguments[0].click();
            """,
            sel.options[-1],
            ent,
        )
        sel.select_by_index(len(sel.options) - 1)

    save_html(
        chrome_driver.page_source,
        export_path / "HTML_FILES",
        filename,
    )

    candidate_urls = list(get_candidate_urls(chrome_driver.page_source))
    extracted = []

    for c_url in tqdm(candidate_urls):
        chrome_driver.get(c_url)
        c_name = c_url.rpartition("/")[-1]
        save_html(
            chrome_driver.page_source, export_path / "HTML_CANDIDATE_FILES", filename, c_name
        )
        extracted.append(extract(chrome_driver.page_source))

    ## Iteration not needed if expanded
    # while True:
    #     senate_next = chrome_driver.find_element(By.ID, "sc_dt_sen_next")
    #     house_next = chrome_driver.find_element(By.ID, "sc_dt_house_next")

    #     for record in extract(chrome_driver.page_source):
    #         if record not in extracted:
    #             extracted.append(record)

    #     if not "disabled" in senate_next.get_attribute("class"):
    #         senate_next.find_element(By.TAG_NAME, "a").click()

    #     elif not "disabled" in house_next.get_attribute("class"):
    #         house_next.find_element(By.TAG_NAME, "a").click()

    #     else:
    #         break

    records_extracted = dict(enumerate(extracted))
    return records_extracted
