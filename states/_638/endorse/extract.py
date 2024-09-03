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
from selenium.common.exceptions import NoSuchElementException


URL = "https://www.plannedparenthoodaction.org/planned-parenthood-advocates-wisconsin/elections/endorsed-candidates"


def extract(page_source, **additional_info):

    soup = BeautifulSoup(page_source, "html.parser")
    cards = soup.select(".tiles-filtered section[data-tile='column']")

    extracted = []

    for card in cards:
        name = card.select_one("h2")
        election = card.select_one("h3")
        bottom_text = card.find(string=lambda text: "Election Date" in text)
        election_date = bottom_text.find_next("span")

        extracted.append(
            {
                "name": name.get_text(strip=True, separator=" "),
                "district": election.get_text(strip=True),
                "election_date": election_date.get_text(strip=True),
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

    # close overlay
    ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

    cookie_banner = chrome_driver.find_element(By.CSS_SELECTOR, "#cookieBanner")

    if cookie_banner:
        cookie_settings = cookie_banner.find_element(
            By.CSS_SELECTOR, "#openCookieBannerSettings"
        )
        cookie_settings.click()
        time.sleep(1)
        reject_all = chrome_driver.find_element(
            By.CSS_SELECTOR, "#CookieBannerSettingsRejectAll"
        )
        reject_all.click()

    else:
        pass


    load_more_btns = chrome_driver.find_elements(
        By.CSS_SELECTOR, ".load-more-tiles .button"
    )

    for i in range(len(load_more_btns)):
        while True:
            load_more_btns = chrome_driver.find_elements(
                By.CSS_SELECTOR, ".load-more-tiles .button"
            )

            visible = load_more_btns[i].is_displayed()

            if visible:
                chrome_driver.execute_script(
                    """
                    arguments[0].scrollIntoView(true)
                    """,
                    load_more_btns[i],
                )
                chrome_driver.execute_script(
                    """
                    btns = document.querySelectorAll(".load-more-tiles .button")
                    btns[arguments[0]].click();
                    """,
                    i,
                )
                time.sleep(1)
            else:
                break
    
    save_html(
        chrome_driver.page_source,
        export_path / "HTML_FILES",
        filename,
    )
    extracted = extract(chrome_driver.page_source)
    records_extracted = dict(enumerate(extracted))

    return records_extracted
