from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys


URL = "https://www.bipec.org/reportcards/"
METHODOLOGY = {"glyphicon-ok": "+", "glyphicon-remove": "-"}


def extract(page_source, **additional_info):

    soup = BeautifulSoup(page_source, "html.parser")
    table = soup.find("table", {"id": "example"})

    def get_text(x):
        return x.get_text(strip=True)

    def translate(s):

        if s.span:
            return METHODOLOGY.get(s.span["class"][-1])
        else:
            return s.get_text(strip=True)

    headers = []
    header_cls = []

    for th in table.thead.find_all("th"):
        if th.span:
            th.span.clear()
        class_ = th["class"].pop()

        header_cls.append(class_)
        headers.append(th.get_text(strip=True))

    extracted = []

    o_i = header_cls.index("thoffice")
    d_i = header_cls.index("thdistrict")

    for row in table.tbody.find_all("tr"):

        columns = row.find_all("td")
        bipec_id = columns[o_i].a["href"].split("=")[-1]

        extracted.append(
            {"bipec_id": bipec_id}
            | dict(zip(headers[: d_i + 1], map(get_text, columns[: d_i + 1])))
            | dict(zip(headers[d_i + 1 :], map(translate, columns[d_i + 1 :])))
            | additional_info
        )

    return extracted


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


def extract_files(files: list[Path]):

    extracted = []

    for file in files:

        with open(file, "r") as f:
            extracted += extract(f.read())

    records_extracted = dict(enumerate(extracted))

    return records_extracted


def main(filename: str, export_path: Path, year: str, html_path: Path = None):

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
    ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

    url_with_year = urljoin(URL, year)

    for office in ("house", "senate"):
        chrome_driver.get(urljoin(url_with_year, f"?c={office}"))

        save_html(
            chrome_driver.page_source,
            export_path / "HTML_FILES",
            filename,
        )
        extracted += extract(chrome_driver.page_source, office=office)

    records_extracted = dict(enumerate(extracted))
    return records_extracted
