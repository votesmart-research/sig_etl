# This is the webscraping script for Progressive Punch, sig_id=2167

from pathlib import Path
from datetime import datetime

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options


URL = "https://www.progressivepunch.org/scores.htm"


def extract(page_source):
    soup = BeautifulSoup(page_source, "html.parser")

    header_section, body = soup.find_all("table", {"id": "all-members"})

    info_headers = header_section.find("tr", {"class": "heading"}).find_all("td")
    sub_headers = header_section.find("tr", {"class": "subheading"}).find_all("td")

    header_text = [
        td.get_text(strip=True) if td else None
        for td in info_headers[:4] + sub_headers[6:8]
    ]

    records = []

    for row in body.find_all("tr"):
        columns = row.find_all("td")
        column_text = [td.get_text(strip=True) for td in columns[:4] + columns[6:8]]
        records.append(dict(zip(header_text, column_text)))

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

    df = pandas.DataFrame.from_dict(extracted, orient='index')
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
    save_html(chrome_driver.page_source, filepath=export_path)

    extracted = extract(chrome_driver.page_source)
    records_extracted = dict(enumerate(extracted))

    return records_extracted


if __name__ == "__main__":

    import argparse
    import pandas

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
        
    save_records(records_extracted, args.export_path, 'Ratings-Extract')
