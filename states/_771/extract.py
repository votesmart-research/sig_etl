# This is the webscraping script for Animal Protection Voters, sig_id = 771

from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup


URLS = {
    "State House": "https://apvnm.org/scorecards/house-scores/",
    "State Senate": "https://apvnm.org/scorecards/senate-scores/",
}


def extract(page_source, **additional_info):

    soup = BeautifulSoup(page_source, "html.parser")

    table = soup.find("table")

    def extract_table(table):
        header = [th.text for th in table.thead.find_all("th")]
        rows = [tr.find_all("td") for tr in table.tbody.find_all("tr")]

        return [
            dict(zip(header, map(lambda x: x.get_text(strip=True), row)))
            | additional_info
            for row in rows
        ]

    return extract_table(table)


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

    extracted = []

    for office, url in URLS.items():

        chrome_driver.get(url)
        # close overlay
        ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

        extracted += extract(chrome_driver.page_source, office=office)

        save_html(
            chrome_driver.page_source,
            export_path / "HTML_FILES",
            filename,
        )

    records_extracted = dict(enumerate(extracted))

    return records_extracted
