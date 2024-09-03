from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from bs4 import BeautifulSoup
from tqdm import tqdm


URL = "http://gachamberscore.com/legislators/"
METHODOLOGY = {
    "yesPos": "+",
    "noPos": "-",
    "legPosCell": "*",
    "presPos": "*",
    "exPos": "*",
}


def extract(page_source, **additional_info) -> list[dict[str, str]]:

    soup = BeautifulSoup(page_source, "html.parser")
    tables = soup.find_all("table", {"class": "resultsTable legListTable"})

    get_text = lambda x: x.get_text(strip=True)

    def _extract(table):

        office = table.parent.find("h2").get_text(strip=True)
        headers = ["sig_candidate_id"] + [
            th.get_text(strip=True) for th in table.thead.find_all("th")
        ]

        rows = []

        for tr in table.tbody.find_all("tr"):
            sig_candidate_id = tr["data-link"].strip("/").rpartition("/")[-1]
            columns = list(map(get_text, tr.find_all("td")))
            rows.append([sig_candidate_id] + columns)

        return [dict(zip(headers, row)) | {"office": office} for row in rows]

    extracted = []

    for table in tables:
        extracted += _extract(table)

    return extracted


def extract_candidate(page_source, **additional_info):

    soup = BeautifulSoup(page_source, "html.parser")

    table = soup.find("table", {"class": "resultsTable legVoteTable"})
    page_link = soup.find("link", {"rel": "canonical"})["href"]

    positions = table.find_all("td", {"class": "legPosCell"}) if table else []
    sig_candidate_id = page_link.strip("/").rpartition("/")[-1] if page_link else ""

    def translate(positions):
        rating_string = []
        for p in positions:
            rating_string.append(str(METHODOLOGY.get(p["class"][-1])))
        return "".join(rating_string)

    return {
        "sig_candidate_id": sig_candidate_id,
        "sig_rating": translate(positions),
    } | additional_info


def extract_files(files: list[Path], candidate_files: list[Path]):

    extracted_table = {}

    for file in tqdm(files, desc="Extracting files..."):
        with open(file, "r") as f:
            _extracted = extract(f.read())
            for r in _extracted:
                extracted_table[r.get("sig_candidate_id")] = r

    extracted = []

    for c_file in tqdm(candidate_files, desc="Extracting candidate files..."):
        with open(c_file, "r") as f:
            candidate_extracted = extract_candidate(f.read())
            e = extracted_table.get(candidate_extracted.get("sig_candidate_id"))
            extracted.append(e | candidate_extracted)

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


def main(
    filename: str,
    export_path: Path,
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

    # close overlay
    ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

    extracted_table = extract(chrome_driver.page_source)

    save_html(
        chrome_driver.page_source,
        export_path / "HTML_FILES",
        filename,
    )

    extracted = []

    for e in tqdm(extracted_table):

        chrome_driver.get(urljoin(URL, e.get("sig_candidate_id")))
        extracted.append(e | extract_candidate(chrome_driver.page_source))

        save_html(
            chrome_driver.page_source,
            export_path / "HTML_CANDIDATE_FILES",
            filename,
            e.get("sig_candidate_id"),
        )

    records_extracted = dict(enumerate(extracted))
    return records_extracted
