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
from selenium.common.exceptions import NoSuchElementException
from tqdm import tqdm


URL = "https://www.reportcard.ndunited.org/legislator-report-card/by-legislator"


def extract(page_source, **additional_info):

    soup = BeautifulSoup(page_source, "html.parser")
    h2s = soup.select(".sqs-html-content h2")
    h4s = soup.select(".sqs-html-content h4")

    page_url = soup.find("link", {"rel": "canonical"})
    name_info = h2s[0].get_text(strip=True) if h2s else None
    score = h4s[0].find("strong") if h4s else None

    return {
        "sig_candidate_id": get_sig_candidate_id(page_url["href"]) if page_url else None,
        "name_info": name_info,
        "sig_rating": score.get_text(strip=True) if score else None,
    }


def get_candidates_urls(page_source):

    soup = BeautifulSoup(page_source, "html.parser")
    ul_list = soup.select(".sqs-html-content ul li")

    for li in ul_list:
        a = li.find("a")
        yield urljoin(URL, a["href"])


def get_sig_candidate_id(url):
    return url.rpartition("/")[-1]


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

    save_html(
        chrome_driver.page_source,
        export_path / "HTML_FILES",
        filename,
    )

    extracted = []
    candidate_urls = list(get_candidates_urls(chrome_driver.page_source))

    for url in tqdm(candidate_urls, desc="Extracting..."):

        chrome_driver.get(url)

        save_html(
            chrome_driver.page_source,
            export_path / "HTML_CANDIDATE_FILES",
            filename,
            get_sig_candidate_id(chrome_driver.current_url)
        )

        e = extract(chrome_driver.page_source)
        extracted.append(e)

    records_extracted = dict(enumerate(extracted))

    return records_extracted
