import time
from datetime import datetime
from pathlib import Path

import pandas
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from tqdm import tqdm


URL = "https://hslf.org/current_scorecard"


def extract_candidate(page_source):

    soup = BeautifulSoup(page_source, "html.parser")

    rep_container = soup.find("div", {"id": "rep"})

    info_container = (
        rep_container.find("div", {"class": "detail"}) if rep_container else None
    )
    info = info_container.find("span", {"class": "eyebrow"}) if info_container else None

    score_container = rep_container.find("div", {"class": "score"})
    score_heading = [
        strong.get_text(strip=True) for strong in score_container.find_all("strong")
    ]
    score_text = [em.get_text(strip=True) for em in score_container.find_all("em")]
    scores = dict(zip(score_heading, score_text))

    return {
        "info": info.get_text(strip=True) if info else None,
    } | scores


def extract(page_source, **additional_info) -> list[dict[str, str]]:

    soup = BeautifulSoup(page_source, "html.parser")
    tables = soup.find_all("table", {"class": "scorecard_table"})

    extracted = []

    def extract_table(table):
        rows = table.tbody.find_all("tr")
        for row in filter(lambda x: x.has_attr("id"), rows):
            columns = row.find_all("td")
            yield {
                "row_id": row["id"],
                "name": "".join(c.get_text(strip=True) for c in columns[:1]),
            } | additional_info

    for table in tables:
        extracted += list(extract_table(table))

    return extracted


def extract_files(files: list[Path]):

    with open(files[0], "r") as f:
        extracted = extract(f.read())

    extracted_d = {e["row_id"]: e for e in extracted}

    for file in files[1:]:
        id_selected = file.name.split("_")[-1].split("-")[0]
        with open(file, "r") as f:
            extracted_d[id_selected].update(extract(f.read()))

    records_extracted = dict(enumerate(extracted))

    return records_extracted


def save_html(page_source, filepath, filename, *additional_info):

    soup = BeautifulSoup(page_source, "html.parser")

    filepath.mkdir(exist_ok=True)

    timestamp = datetime.strftime(datetime.now(), "%Y-%m-%d-%H%M%S-%f")

    with open(
        filepath / f"{filename}_{'-'.join(map(str, additional_info))}"
        f"{'-' if additional_info else ''}{timestamp}.html",
        "w",
    ) as f:
        f.write(str(soup))


def save_records(extracted: dict[int, dict[str, str]], filepath, filename):

    filepath.mkdir(exist_ok=True)

    timestamp = datetime.strftime(datetime.now(), "%Y-%m-%d-%H%M%S-%f")

    df = pandas.DataFrame.from_dict(extracted, orient="index")
    df.to_csv(
        filepath / f"{filename}_{timestamp}.csv",
        index=False,
    )


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

    time.sleep(2)

    extracted = extract(chrome_driver.page_source)
    save_html(
        chrome_driver.page_source,
        export_path / "HTML_FILES",
        filename,
    )

    for e in tqdm(extracted):
        id_to_select = e["row_id"].replace(".", "\\\\.")
        id_to_select = id_to_select.replace(" ", "\\\\ ")

        not_clicked = chrome_driver.execute_script(
            f"candidateRow = document.querySelector('#{id_to_select}');"
            """
        if (candidateRow!=null) {
            candidateRow.click();
        }
        else{
            return true;
        }
        """
        )
        if not_clicked:
            print("Candidate not extracted: ", id_to_select)
            continue

        sig_candidate_id = "-".join(e["row_id"].replace(" ", "").split("_"))

        e.update(extract_candidate(chrome_driver.page_source))
        save_html(
            chrome_driver.page_source,
            export_path / "HTML_FILES_CANDIDATES",
            filename,
            sig_candidate_id,
        )

    records_extracted = dict(enumerate(extracted))

    return records_extracted
