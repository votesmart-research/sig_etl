from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urljoin

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

from tqdm import trange


URL = "https://www.ntu.org/ratecongress/legislator/SearchResult/"


def extract(page_source, **additional_info):

    soup = BeautifulSoup(page_source, "html.parser")
    table = soup.find("table")

    all_rows = table.select("tbody tr")

    headers = [th.get_text(strip=True) for th in all_rows[0].select("th")]
    rows = [tr.select("td") for tr in all_rows[1:]]

    return [
        dict(zip(headers, [c.get_text(strip=True) for c in row])) | additional_info
        for row in rows
    ]


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

    pagination_links = chrome_driver.find_elements(
        By.CSS_SELECTOR, "ul.pagination a.pagination-link"
    )

    last_page_url = urlparse(pagination_links[-1].get_attribute("href"))
    params = parse_qs(last_page_url.query)
    last_page = params.get("page").pop()

    extracted = []

    for n in trange(1, int(last_page)):
        chrome_driver.get(urljoin(URL, f"?page={n}"))
        extracted += extract(chrome_driver.page_source)

        save_html(
            chrome_driver.page_source,
            export_path / "HTML_FILES",
            filename,
            f"page-{n}",
        )
    records_extracted = dict(enumerate(extracted))

    return records_extracted
