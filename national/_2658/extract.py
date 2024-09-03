from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains


from tqdm import tqdm


URL = "https://catholicvote.org/cap/scorecard/"
METHODOLOGY = {"positive": "+", "negative": "-"}


def extract(page_source, **additional_info):

    soup = BeautifulSoup(page_source, "html.parser")
    name_grade = soup.select_one(".ms-scorer-block")
    party_state = soup.select_one(".ms-scorer-party-info")

    name = name_grade.h1
    grade = name_grade.select_one(".ms-rating")
    scores = soup.select("span.ms-symbol-score")

    sig_rating = []

    for score in scores:
        score_text = score.get_text(strip=True)
        transformed_score = METHODOLOGY.get(score_text)
        sig_rating.append(transformed_score if transformed_score else "*")

    def translate(scores):
        positives = len(list(filter(lambda x: x == "+", scores)))
        negatives = len(list(filter(lambda x: x == "-", scores)))

        if not (positives or negatives):
            return None
        return round(positives / (positives + negatives) * 100)

    return {
        "name": name.get_text(strip=True),
        "grade": grade.get_text(strip=True),
        "party_state": party_state.get_text(strip=True),
        "sig_rating": "".join(sig_rating),
        "our_rating": translate(sig_rating),
    } | additional_info


def get_candidates_urls(page_source):
    soup = BeautifulSoup(page_source, "html.parser")
    scorecard_wraps = soup.select(".ms-scoredcard-list-wrap")

    candidate_urls = {}

    for wrap in scorecard_wraps:
        office = wrap.select_one(".ms-heading-h2")
        scorecard_items = wrap.select(".ms-scoredcard-item")
        candidate_links = [s_item.find("a").get("href") for s_item in scorecard_items]
        candidate_urls[office.get_text(strip=True)] = candidate_links

    return candidate_urls


def extract_files(files: list[Path]):

    extracted = []

    for file in files:
        with open(file, "r") as f:
            extracted.append(extract(f.read()))

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

    candidate_urls = get_candidates_urls(chrome_driver.page_source)

    extracted = []

    for office, urls in tqdm(candidate_urls.items(), desc="Extracting..."):
        for url in tqdm(urls, desc=f"{office}"):
            chrome_driver.get(url)
            extracted.append(extract(chrome_driver.page_source, office=office))
            
            save_html(
                chrome_driver.page_source,
                export_path / "HTML_FILES",
                filename,
            )

    records_extracted = dict(enumerate(extracted))
    return records_extracted
