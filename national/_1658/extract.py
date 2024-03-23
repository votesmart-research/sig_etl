from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from bs4 import BeautifulSoup


URLS = [
    "https://www.freedomworks.org/house-scorecard/",
    "https://www.freedomworks.org/senate-scorecard/",
]


def extract(page_source):

    soup = BeautifulSoup(page_source, "html.parser")

    table = soup.find("table", {"class": "vote-table"})
    articles = table.find_all("article", {"class": "legislator-score-card"})

    def _extract_article(article: BeautifulSoup):
        sig_candidate_id = article["id"]
        candidate_name = article.find("p", {"class": "card-name"}).text
        card_info = article.find_all("span", {"class": "meta-item"})
        office = card_info[0].text
        district = card_info[-1].text
        scores = article.find_all("li", {"class": "card-score"})

        return {
            "sig_candidate_id": sig_candidate_id,
            "candidate_name": candidate_name,
            "office": office,
            "district": district,
        } | {score.span.text: score.strong.text.strip() for score in scores}

    extracted = [_extract_article(article) for article in articles]

    return extracted


def extract_files(files: list):

    extracted = []

    for file in files:

        with open(file, "r") as f:
            extracted += extract(f.read())

    return extracted


def save_html(
    page_source,
    filepath: Path,
    filename: str,
    *additional_info,
):

    soup = BeautifulSoup(page_source, "html.parser")

    filepath = filepath / "HTML_FILES"
    filepath.mkdir(exist_ok=True)

    timestamp = datetime.strftime(datetime.now(), "%Y-%m-%d-%H%M%S-%f")

    with open(
        filepath / f"{filename}_{'-'.join(map(str, additional_info))}"
        f"{'-' if additional_info else ''}{timestamp}.html",
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

    for url in URLS:
        chrome_driver.get(url)

        # close overlay
        ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()
        office = chrome_driver.current_url.rstrip("/").split("/")[-1]

        extracted += extract(chrome_driver.page_source)
        save_html(
            chrome_driver.page_source,
            export_path / "HTML_FILES",
            filename,
            office,
        )

    records_extracted = dict(enumerate(extracted))
    return records_extracted
