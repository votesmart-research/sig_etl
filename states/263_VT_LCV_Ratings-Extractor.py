import requests
import pandas
from datetime import datetime
from bs4 import BeautifulSoup


MAIN_URL = "https://vermontconservationvoters.com/legislative-scorecard"


def file_to_soup(filepath) -> BeautifulSoup:

    with open(filepath, 'r') as f:
        content = f.read()

    soup  = BeautifulSoup(content, 'html.parser')

    return soup


def request_to_soup(url) ->  BeautifulSoup:
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')

    return soup


def save_page_source(soup: BeautifulSoup, filename):
    pretty_html = soup.prettify()

    with open (filename, 'w') as f:
        f.write(pretty_html)


def extract(soup: BeautifulSoup) -> list:

    senate_rows = soup.find('div', {'id':'senateTab'}).find('tbody').find_all('tr')
    house_rows = soup.find('div', {'id':'houseTab'}).find('tbody').find_all('tr')
    th_s = [th.text.strip() for th in soup.find('thead').find_all('th')]

    def _extract_row(row, office):
        td_s = [td.text.strip() for td in row.find_all('td')]
        return dict(zip(th_s, td_s)) | {'Office': office}

    extracted = [_extract_row(row, 'State Senate') for row in senate_rows] + \
                [_extract_row(row, 'State House') for row in house_rows]

    return extracted


def main(source, from_file: bool) -> None:

    if from_file:
        soup = file_to_soup(source)
        timestamp = ''
    else:
        soup = request_to_soup(source)
        timestamp = f"_{datetime.now().strftime('%Y-%m-%d-%H%M')}"
        save_page_source(soup, f'_VT_LCV_Ratings{timestamp}.html')

    records = extract(soup)

    pandas.DataFrame.from_records(records).to_csv(f'_VT_LCV_Ratings-Extract{timestamp}.csv', index=False)


if __name__ == "__main__":
    import sys
    import os

    script, source = sys.argv

    main(source, os.path.isfile(source))