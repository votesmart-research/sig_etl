from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import pandas
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


URL = "https://scorecard.cwa-union.org/legislators"


def get_last_page(page_source):
    soup = BeautifulSoup(page_source, "html.parser")

    e = soup.find("li", {"class": "pager__item--last"})
    last_page_url = e.a["href"].strip("?") if e else ""
    params = [p.split("=") for p in last_page_url.split("&")] if last_page_url else []
    cleaned_params = {p: v for p, v in params} if params else {}

    return int(cleaned_params["page"]) if "page" in cleaned_params else 0


def extract(page_source, **additional_info):
    soup = BeautifulSoup(page_source, "html.parser")

    def extract_table(table):
        if not table:
            return []

        headers = [th.get_text(strip=True) for th in table.thead.find_all("th")[1:]]

        def get_text(x):
            return x.get_text(strip=True)

        for tr in table.tbody.find_all("tr"):
            columns = tr.find_all("td")[1:]
            name_el = columns[0].a if columns else ""
            name_text = name_el.get_text(strip=True)
            candidate_id = name_el["href"].rpartition("/")[-1]

            yield {
                "candidate_id": candidate_id,
                "Name": name_text,
            } | dict(zip(headers[1:], map(get_text, columns[1:])))| additional_info


    table_parent = soup.find("div", {"class": "legislator-table"})
    table = table_parent.table if table_parent else None

    return extract_table(table)


def extract_files(files: list):
    extracted = []

    for file in files:
        with open(file, "r") as f:
            extracted += extract(f.read())

    return extracted


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


def save_extract(extracted: list[dict], filepath, *additional_info):
    filepath = Path(filepath) / "EXTRACT_FILES"
    filepath.mkdir(exist_ok=True)

    timestamp = datetime.strftime(datetime.now(), "%Y-%m-%d-%H%M%S-%f")

    df = pandas.DataFrame.from_records(extracted)
    df.to_csv(
        filepath / f"Ratings-Extract_{'-'.join(map(str, additional_info))}"
        f"{'-' if additional_info else ''}{timestamp}.csv",
        index=False,
    )


def main(export_dir, span):
    chrome_service = Service()
    chrome_options = Options()
    chrome_options.add_argument("incognito")
    # chrome_options.add_argument("headless")
    chrome_driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    chrome_driver.get(URL)

    # close overlay
    ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

    extracted = []
    office_ref = {1: "House", 2: "Senate"}

    for i in range(1, 3):
        current_url = urljoin(URL, f"?chamber={i}&year={span}")
        chrome_driver.get(current_url)

        for n in range(0, get_last_page(chrome_driver.page_source) + 1):
            chrome_driver.get(current_url + f"&page={n}")
            extracted += extract(chrome_driver.page_source)
            save_html(chrome_driver.page_source, export_dir, f"{office_ref[i]}-{n}")

    return extracted


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(prog="sig_webscrape")
    parser.add_argument(
        "-d",
        "--exportdir",
        type=Path,
        required=True,
        help="file directory of where the files exports to",
    )
    parser.add_argument(
        "-s", "--span", type=Path, help="years/span of the ratings", required=True
    )
    parser.add_argument(
        "-f", "--htmldir", type=Path, help="file directory of html files to read"
    )

    args = parser.parse_args()

    if args.htmldir:
        html_files = filter(
            lambda f: f.name.endswith(".html"),
            (args.exportdir / args.htmldir).iterdir(),
        )
        extracted = extract_files(sorted(html_files, key=lambda x: x.stat().st_ctime))
    else:
        extracted = main(args.exportdir, args.span)

    save_extract(extracted, args.exportdir)
