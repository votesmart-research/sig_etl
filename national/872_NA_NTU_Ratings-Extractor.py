from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urljoin
from tqdm import trange


import pandas
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains


URL = "https://www.ntu.org/ratecongress/legislator/SearchResult/"


def get_last_page(page_source):
    soup = BeautifulSoup(page_source, "html.parser")

    pagination_links = soup.find_all("a", {"class": "pagination-link"})
    e = urlparse(pagination_links[-1]["href"]) if pagination_links else urlparse(URL)

    last_page_url = e.query.strip("?") if e.query else ""
    params = [p.split("=") for p in last_page_url.split("&")] if last_page_url else []
    cleaned_params = {p: v for p, v in params} if params else {}

    return int(cleaned_params["page"]) if "page" in cleaned_params else 0


def extract(page_source, **additional_info):
    soup = BeautifulSoup(page_source, "html.parser")

    table = soup.find("table", {"class": "table-block"})

    def extract_table(table):
        all_rows = table.tbody.find_all("tr")

        headers = [th.get_text(strip=True) for th in all_rows[0].find_all("th")]
        rows = [tr.find_all("td") for tr in all_rows[1:]]

        def get_text(x):
            return x.get_text(strip=True)

        return [
            dict(zip(headers, map(get_text, row))) | additional_info for row in rows
        ]

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


def main(export_dir):
    chrome_service = Service()
    chrome_options = Options()
    chrome_options.add_argument("incognito")
    # chrome_options.add_argument('headless')
    chrome_driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    chrome_driver.get(URL)

    # close overlay
    ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

    extracted = []
    
    for n in trange(1, get_last_page(chrome_driver.page_source)):
        chrome_driver.get(urljoin(URL, f"?page={n}"))
        extracted += extract(chrome_driver.page_source)
        save_html(chrome_driver.page_source, export_dir, "page-{n}")

    return extracted


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(prog="sig_webscrape")
    parser.add_argument(
        "-e",
        "--exportdir",
        type=Path,
        required=True,
        help="file directory of where the files exports to",
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
        extracted = main(args.exportdir)

    save_extract(extracted, args.exportdir)
