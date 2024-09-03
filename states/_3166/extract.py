from datetime import datetime
from pathlib import Path

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


# Rating Strings Translation
RS_METHODOLOGY = {
    # Former Sponsor
    "229315402c4e065b2770daa901b73097": "Gold",
    "001-former-sponsor-legalization": "Gold",
    # Former Vote
    "0fe035d9d4daafbbc2fac86bd94a26df": "Silver",
    "001-former-vote-legalization": "Silver",
    # Support - Legalization
    "5300257d2fb7e56828af490571ffdac6": "Support",
    "001-yes-legalization": "Support",
    # Support - Home
    "daf31dc2958d52cb698fac8ba1350efe": "Support",
    "001-yes-home-grow": "Support",
    # Oppose - Legalization
    "e559e453f22434458dde54ee96d8a7b4": "Oppose",
    "001-no-legalization": "Oppose",
    # Oppose - Home
    "269869db38823bc3c658bb0615862392": "Oppose",
    "12e06e9263393320473e1b39a125a55c": "Oppose",
    "001-moveable-no-home-grow": "Oppose",
    "001-no-home-grow": "Oppose",
    # Did not respond - Legalization
    "9655a0e8b70c26fe9686ad99cd04b2d2": "Unknown",
    "001-NO-RESPONSE-legalization": "Unknown",
    # Did not respond - Home
    "6d218c14c61a692501237b11f9d4b585": "Unknown",
    "001-NO-RESPONSE-home-grow": "Unknown",
    # Undecided - Legalization
    "a248d733964c95d41e833d9c5f63be60": "Unknown",
    "001-undecided-legalization": "Unknown",
    # Undecided - Home
    "ef7daa2dfc9ff6cb86ef7975a431dbba": "Unknown",
    "001-undecided-home-grow": "Unknown",
}

RS_TRANSLATE = {
    "Gold": "+++",
    "Silver": "++",
    "Support": "+",
    "Oppose": "-",
    "Unknown": "*",
}


def translate_rs(string):
    found_key = filter(lambda x: x in string, RS_METHODOLOGY)
    found_value = RS_METHODOLOGY.get("".join(found_key))
    translated = RS_TRANSLATE.get(found_value)
    return translated if translated is not None else string


def extract(page_source, **additional_info):

    soup = BeautifulSoup(page_source, "html.parser")
    row_grids = soup.select(".row.gridblock")

    current_office_dist = None
    extracted = []

    for row_grid in row_grids:
        candidate_columns = row_grid.select(".col-md-3")

        if not candidate_columns:
            info = row_grid.find("h2")
            if info:
                current_office_dist = info
            continue

        for col in candidate_columns:
            name = col.find("h3")
            imgs = col.find_all("img")
            translated_imgs = []
            not_translated_imgs = []
            for img in imgs[1:]:
                src = img["src"]
                img_name = src.rpartition("/")[-1].strip().rstrip(".jpg").rstrip(".png")
                t = translate_rs(img_name)

                if t != img_name:
                    translated_imgs.append(t)
                else:
                    not_translated_imgs.append(t)

            grade = None
            unknown_score = None

            if len(not_translated_imgs) > 1:
                unknown_score = "; ".join(not_translated_imgs)
            else:
                grade = "".join(not_translated_imgs)

            if name is not None:
                extracted.append(
                    {
                        "name": name.get_text(strip=True),
                        "office_district": (
                            current_office_dist.get_text(strip=True)
                            if current_office_dist
                            else None
                        ),
                        "grade": grade,
                        "unknown_score": unknown_score,
                        "sig_rating": "".join(translated_imgs),
                    }
                    | additional_info
                )

    return extracted


def extract_files(files: list[Path]):

    extracted = []

    for file in files:

        with open(file, "r") as f:
            extracted += extract(f.read())

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


def main(urls: str, filename: str, export_path: Path, html_path: Path = None):

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

    # close overlay
    ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

    extracted = []

    for url in urls:
        chrome_driver.get(url)
        office = url.strip("/").rpartition("/")[-1]

        extracted += extract(chrome_driver.page_source, office=office)

        save_html(
            chrome_driver.page_source,
            export_path / "HTML_FILES",
            filename,
            office,
        )

    records_extracted = dict(enumerate(extracted))

    return records_extracted
