# This is the webscrape for American Civil Liberties Union (ACLU), sig_id=1378

import time
import pandas
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup


URL = "https://www.aclu.org/scorecard/?filter=all"


def extract(page_source):

    soup = BeautifulSoup(page_source, "html.parser")
    all_states = soup.find_all("div", {"class": "state-results"})

    records = []

    for state in all_states:

        candidates = state.find_all("a")

        for candidate in candidates:

            score = candidate.find("p", {"class": "score"})
            party = candidate.find("div", {"class": "party"})
            name = candidate.find("div", {"class": "name"})
            district = candidate.find("div", {"class": "office"})

            records.append(
                {
                    "name": name.text.strip() if name else None,
                    "party": party.text.strip() if party else None,
                    "district": district.text.strip() if district else None,
                    "score": score.text.strip() if score else None,
                    "state": state.h3.text.strip() if state.h3 else None,
                }
            )

    return records


def extract_files(files: list):

    extracted = []

    for file in files:

        with open(file, "r") as f:
            extracted += extract(f.read())

    records_extracted = dict(enumerate(extracted))

    return records_extracted


def save_html(page_source, filepath, *additional_info):

    soup = BeautifulSoup(page_source, "html.parser")

    filepath = Path(filepath) / "HTML_FILES"
    filepath.mkdir(exist_ok=True)

    timestamp = datetime.strftime(datetime.now(), "%Y-%m-%d-%H%M%S-%f")

    with open(
        filepath / f"Ratings_{'-'.join(map(str, additional_info))}"
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


def main(export_path):

    chrome_service = Service()
    chrome_options = Options()
    chrome_options.add_argument("incognito")
    chrome_options.add_argument("headless")
    chrome_driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    chrome_driver.get(URL)

    html = chrome_driver.find_element(By.TAG_NAME, "html")

    counter = 0

    while True:

        html.send_keys(Keys.END)
        time.sleep(0.75)

        temp_counter = chrome_driver.execute_script(
            """
            return document.querySelectorAll('.state-results').length
        """
        )

        if not (temp_counter - counter):
            break

        counter += temp_counter - counter

    save_html(chrome_driver.page_source, export_path)
    extracted = extract(chrome_driver.page_source)

    records_extracted = dict(enumerate(extracted))

    return records_extracted


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(prog="sig_webscrape")

    parser.add_argument(
        "-d",
        "--export_path",
        type=Path,
        help="Filepath for files to export to.",
    )
    parser.add_argument(
        "-f",
        "--html_dir",
        type=Path,
        help="Directory of html files.",
    )

    args = parser.parse_args()

    if args.html_dir:
        html_files = filter(
            lambda f: f.name.endswith(".html"),
            (args.export_path / args.html_dir).iterdir(),
        )
        records_extracted = extract_files(
            sorted(html_files, key=lambda x: x.stat().st_ctime)
        )
    else:
        records_extracted = main(args.export_path)

    save_records(records_extracted, args.export_path, "Ratings-Extract")
