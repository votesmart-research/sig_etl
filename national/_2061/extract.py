from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, urljoin

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from tqdm import tqdm


URL = "https://heritageaction.com/scorecard/members"


def extract_scores(page_source):

    soup = BeautifulSoup(page_source, "html.parser")

    scores = soup.find_all("div", {"class": "member-stats__item"})
    scores_text = {
        score.span.get_text(strip=True): score.div.get_text(strip=True)
        for score in scores[:2]
    }

    return scores_text


def extract_info(page_source):

    soup = BeautifulSoup(page_source, "html.parser")
    table = soup.find("table")

    headers = (
        ["sig_candidate_id"]
        + [th.get_text(strip=True) for th in soup.thead.find_all("th")[:-2]]
        + ["candidate_url"]
    )

    def get_text(x):
        return x.get_text(strip=True)

    extracted = []

    for tr in table.tbody.find_all("tr"):
        columns = tr.find_all("td")[:-2]
        candidate_url = urlparse(urljoin(URL, columns[0].a["href"]))
        sig_candidate_id = candidate_url.path.strip("/").split("/")[-2]
        row = (
            [sig_candidate_id] + list(map(get_text, columns)) + [candidate_url.geturl()]
        )

        extracted.append(dict(zip(headers, row)))

    return extracted


def extract_files(files: list[Path]):

    extracted = []

    with open(files[0], "r") as f:
        candidate_info = extract_info(f.read())

    info_ref = {info["sig_candidate_id"]: info for info in candidate_info}

    for file in tqdm(files[1:]):
        with open(file, "r") as f:
            page_source = f.read()
            sig_candidate_id = file.name.split("_")[-1].split("-")[0]
            extracted.append(info_ref[sig_candidate_id] | extract_scores(page_source))

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

    candidate_info = extract_info(chrome_driver.page_source)
    save_html(
        chrome_driver.page_source,
        export_path / "HTML_FILES",
        filename,
    )

    extracted = []

    for info in tqdm(candidate_info):
        chrome_driver.get(info["candidate_url"])
        extracted.append(info | extract_scores(chrome_driver.page_source))
        save_html(
            chrome_driver.page_source,
            export_path / "HTML_FILES",
            filename,
            info["sig_candidate_id"],
        )

    records_extracted = dict(enumerate(extracted))
    return records_extracted
