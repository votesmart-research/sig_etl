from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
from pypdf import PdfWriter

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.common.exceptions import NoSuchElementException

from tqdm import tqdm

URL = "https://foac-pac.org/Voter-Guide"


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

    # if html_path:
    #     html_files = filter(
    #         lambda f: f.name.endswith(".html"),
    #         (export_path / html_path).iterdir(),
    #     )
    #     records_extracted = extract_files(
    #         sorted(html_files, key=lambda x: x.stat().st_ctime)
    #     )
    #     return records_extracted

    download_dir = Path.home() / "Downloads" / "PDF_FILES"
    download_dir.mkdir(exist_ok=True)

    chrome_service = Service()
    chrome_options = Options()
    chrome_options.add_argument("incognito")
    chrome_options.add_argument("headless")
    chrome_options.add_argument("disable-gpu")
    chrome_options.add_argument("no-sandbox")
    chrome_options.add_argument("ignore-ssl-errors=yes")
    chrome_options.add_argument("ignore-certificate-errors")

    chrome_prefs = {
        "download.default_directory": str(
            download_dir
        ),  # Set the download folder relative to home
        "profile.content_settings.exceptions.automatic_downloads.*.setting": 1,  # Enable automatic downloads
        "download.prompt_for_download": False,  # Don't prompt for download
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True,  # Ensure PDFs are downloaded instead of viewed
        # "profile.content_settings.exceptions.automatic_downloads.*": {"setting": 1},
    }

    chrome_options.add_experimental_option("prefs", chrome_prefs)

    chrome_driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    chrome_driver.get(URL)

    # time.sleep(5)

    # close overlay
    ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()

    save_html(
        chrome_driver.page_source,
        export_path / "HTML_FILES",
        filename,
    )

    select = Select(chrome_driver.find_element(By.CSS_SELECTOR, "#vg_select"))

    federal_urls = []
    state_urls = []

    for option in tqdm(select.options[1:], desc="Collecting URLs..."):
        option.click()
        form_holder = WebDriverWait(chrome_driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "#form_holder"))
        )

        links = form_holder.find_elements(By.CSS_SELECTOR, "a")

        federal_urls.append(urljoin(URL, links[0].get_attribute("href")))
        state_urls.append(urljoin(URL, links[-1].get_attribute("href")))

        close_btn = form_holder.find_element(By.CSS_SELECTOR, "#close_guides")
        close_btn.click()

        WebDriverWait(chrome_driver, 10).until(
            EC.invisibility_of_element((By.CSS_SELECTOR, "#form_holder"))
        )

    federal_download_dir = download_dir / "Federal"
    states_download_dir = download_dir / "States"

    federal_download_dir.mkdir(exist_ok=True)
    states_download_dir.mkdir(exist_ok=True)

    chrome_driver.execute_cdp_cmd(
        "Page.setDownloadBehavior",
        {"behavior": "allow", "downloadPath": str(federal_download_dir)},
    )

    for url in tqdm(federal_urls, desc="Downloading Federal PDFs..."):
        chrome_driver.get(url)

    chrome_driver.execute_cdp_cmd(
        "Page.setDownloadBehavior",
        {"behavior": "allow", "downloadPath": str(states_download_dir)},
    )

    for url in tqdm(state_urls, desc="Downloading States PDFs..."):
        chrome_driver.get(url)

    return []
