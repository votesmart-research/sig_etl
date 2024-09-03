import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

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

URL = "https://ipaagrassroots.org/voting-records"


def extract(page_source, **additional_info) -> list[dict]:

    soup = BeautifulSoup(page_source, "html.parser")
    table = soup.find("table")

    headers = [th.get_text(strip=True) for th in table.thead.find_all("th")]
    rows = [tr.find_all("td") for tr in table.tbody.find_all("tr")[2:]]

    def get_text(x):
        return x.get_text(strip=True)

    extracted = []

    # Only select until the header before "Position"
    pos = headers.index("Position")
    pos_score = headers.index("Score")
    selected_headers = headers[:pos] + headers[pos_score : pos_score + 1]

    for row in rows[2:]:
        selected_columns = row[:pos] + row[-1:]
        extracted.append(
            {"candidate_url": urljoin(URL, row[0].a.get("href"))}
            | dict(zip(selected_headers, map(get_text, selected_columns)))
            | additional_info
        )

    return extracted


def extract_candidate(page_source, **additional_info) -> dict:
    soup = BeautifulSoup(page_source, "html.parser")
    office = soup.select_one(".candidate-office")
    lifetime_score = soup.select_one(".candidate-score .score")

    return {
        "office": office.get_text(strip=True) if office else None,
        "sig_lifetime": lifetime_score.get_text(strip=True) if lifetime_score else None,
    } | additional_info


def extract_files(files: list[Path], candidate_files: list[Path]):

    extracted = []

    for file in tqdm(files, desc="Extracting files..."):
        with open(file, "r") as f:
            session = "-".join(file.name.split("_")[-1].split("-")[:-6])
            extracted += extract(f.read(), session=session)

    candidate_extracted = {}

    for c_file in tqdm(candidate_files, desc="Extracting candidate files..."):
        with open(c_file, "r") as f:
            sig_candidate_id = "".join(c_file.name.split("_")[-1].split("-")[:-5])
            candidate_extracted[sig_candidate_id] = extract_candidate(
                f.read(), sig_candidate_id=sig_candidate_id
            )

    for e in tqdm(extracted, desc="Combining files..."):
        sig_candidate_id = e.pop("candidate_url").rpartition("/")[-1]
        if sig_candidate_id in candidate_extracted:
            e.update(candidate_extracted.get(sig_candidate_id))
        else:
            e.update({"sig_candidate_id": sig_candidate_id})

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


def main(
    filename: str,
    export_path: Path,
    sessions: list | set,
    html_path: Path = None,
    candidates_html_path: Path = None,
):

    if html_path and candidates_html_path:
        html_files = filter(
            lambda f: f.name.endswith(".html"),
            (export_path / html_path).iterdir(),
        )
        candidate_html_files = filter(
            lambda f: f.name.endswith(".html"),
            (export_path / candidates_html_path).iterdir(),
        )
        records_extracted = extract_files(
            sorted(html_files, key=lambda x: x.stat().st_ctime),
            sorted(candidate_html_files, key=lambda x: x.stat().st_ctime),
        )

        return records_extracted

    chrome_service = Service()
    chrome_options = Options()
    chrome_options.add_argument("incognito")
    chrome_options.add_argument("headless")
    chrome_driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    chrome_driver.get(URL)
    time.sleep(10)

    # close overlay
    ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

    selected_options = []

    session_options = chrome_driver.execute_script(
        """
        return document.querySelectorAll("select[name='congress']>option")
        """
    )

    for session in sessions:
        for option in session_options:
            if session in option.text and option not in selected_options:
                selected_options.append(option)

    extracted = []

    for o in tqdm(selected_options):
        o.click()

        WebDriverWait(chrome_driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "table"))
        )
        while True:

            next_button = chrome_driver.execute_script(
                """
                paginateButtons = document.querySelectorAll(".pagination>li")
                nextContainer = paginateButtons[paginateButtons.length-1]

                if (nextContainer.classList.contains('disabled')){
                    return null
                }
                else{
                    return nextContainer.querySelector('a')   
                }
                """
            )
            selected_page = chrome_driver.find_element(
                By.CSS_SELECTOR, ".page-item.active"
            )

            save_html(
                chrome_driver.page_source,
                export_path / "HTML_FILES",
                filename,
                o.text,
                selected_page.text,
            )

            extracted += extract(chrome_driver.page_source, session=o.text)

            if next_button is not None:
                next_button.click()
            else:
                break

    for e in tqdm(extracted, desc="Extracting Candidates..."):

        candidate_url = e.pop("candidate_url")
        chrome_driver.get(candidate_url)
        candidate_id = candidate_url.rpartition("/")[-1]

        try:
            WebDriverWait(chrome_driver, 10).until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, "div[ng-if='officials.currentOfficial']")
                )
            )
        except TimeoutException:
            continue

        save_html(
            chrome_driver.page_source,
            export_path / "HTML_FILES_CANDIDATE",
            filename,
            candidate_id,
        )

        e |= extract_candidate(chrome_driver.page_source, candidate_id=candidate_id)

    records_extracted = dict(enumerate(extracted))

    return records_extracted
