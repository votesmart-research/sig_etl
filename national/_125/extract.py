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
from unidecode import unidecode

from tqdm import tqdm


URL = "https://www.uscpraction.org/scorecard"


def extract(page_source, **additional_info):

    soup = BeautifulSoup(page_source, "html.parser")

    info_elements = soup.select("div.w-\\[66\\.66\\%\\] > div")

    info = info_elements[0]
    grades = info_elements[-1]

    name = info.h3.get_text(strip=True, separator=";")
    other_info = info.p.get_text(strip=True, separator=";")

    grades_d = {}
    for div in grades.select("div"):
        spans = div.select("span")
        grade = spans[0]
        grade_title = spans[-1]
        grades_d.update({grade_title.get_text(strip=True): grade.get_text(strip=True)})

    def calculate_record(el):

        good_votes = el.select("span.bg-green")
        bad_votes = el.select("span.bg-light-red")
        neutral_vote = el.select("span.bg-")

        good_count = 0
        bad_count = 0

        text_of = lambda e: unidecode(e.get_text(strip=True)).lower()
        # As of making this script, their methodology only counts votes as good and bad score, sponsor
        # bills do not count.
        for g in good_votes:
            if "yea" in text_of(g) or "nay" in text_of(g):
                good_count += 1

        for b in bad_votes:
            if "yea" in text_of(b) or "nay" in text_of(b):
                bad_count += 1

        for n in neutral_vote:
            if "present" in text_of(n) or "not voting" in text_of(n):
                good_count += 0.5

        if good_count + bad_count == 0:
            return 0, 0

        return good_count / (good_count + bad_count) * 100

    voting_record = soup.find(string="Voting Record").parent.parent
    voting_score = calculate_record(voting_record)

    return {
        "name": name,
        "info": other_info,
        "total_score": voting_score,
    } | grades_d


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

    iframe = chrome_driver.find_element(By.CSS_SELECTOR, "iframe")
    chrome_driver.switch_to.frame(iframe)

    btn_see_all = chrome_driver.find_element(
        By.XPATH, "//button[contains(text(), 'See All')]"
    )
    btn_see_all.click()

    button_house = lambda d: d.find_element(By.XPATH, "//button[text()='House']")
    button_senate = lambda d: d.find_element(By.XPATH, "//button[text()='Senate']")

    extracted = []

    for _btn in (button_house, button_senate):

        btn = _btn(chrome_driver)
        btn.click()

        save_html(
            chrome_driver.page_source,
            export_path / "HTML_FILES",
            filename,
            btn.text.title(),
        )

        candidate_cards = chrome_driver.find_elements(
            By.CSS_SELECTOR, "div[role=button]"
        )
        p_bar = tqdm(
            total=len(candidate_cards), desc=f"Extracting...{btn.text.title()}"
        )

        while True:

            candidate_cards = chrome_driver.find_elements(
                By.CSS_SELECTOR, "div[role=button]"
            )
            candidate_cards[p_bar.n].click()

            voting_container = chrome_driver.find_element(
                By.XPATH, "//p[text()='Voting Record']"
            ).parent
            track_container = chrome_driver.find_element(
                By.XPATH, "//p[text()='Track Record']"
            ).parent

            try:
                btn_see_all_votes = voting_container.find_element(
                    By.XPATH, "//button[contains(text(), 'See All')]"
                )
                btn_see_all_votes.click()
            except NoSuchElementException:
                pass

            try:
                btn_see_all_track = track_container.find_element(
                    By.XPATH, "//button[contains(text(), 'See All')]"
                )
                btn_see_all_track.click()
            except NoSuchElementException:
                pass

            extracted.append(extract(chrome_driver.page_source))

            btn_back = chrome_driver.find_element(
                By.XPATH, "//button[span[contains(text(), 'Back to Search')]]"
            )

            btn_back.click()
            p_bar.update(1)

            save_html(
                chrome_driver.page_source,
                export_path / "HTML_CANDIDATE_FILES",
                filename,
            )

            if p_bar.n == len(candidate_cards):
                break

    records_extracted = dict(enumerate(extracted))

    return records_extracted
