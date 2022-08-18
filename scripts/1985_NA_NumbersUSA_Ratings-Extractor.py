# This is the webscraping script for NumbersUSA, sig_id=1985

import requests
import pandas
from bs4 import BeautifulSoup


MAIN_URL = "https://www.numbersusa.com/content/my/tools/grades/list/"


def extract(soup):
    name_sections = soup.find_all('a')

    records = []
    
    for a in name_sections:
        numberusa_id = a['href'].split('/')[-3]
        name = a.text.strip() if a else None
        info = a.find_next() if a else None
        score = info.next_sibling if info else None

        records.append({'numberusa_id': numberusa_id,
                        'name': name,
                        'info': info.text.strip() if info else None,
                        'score': score.text.strip() if score else None})

    return records


def soup_to_file(soup, filename):
    with open(filename, 'w') as f:
        f.write(soup.prettify())


def main():
    page_source = requests.get(MAIN_URL).text
    soup = BeautifulSoup(page_source, 'html.parser')

    current_session = soup.find('div', {'id':'tabset-1'})
    lifetime = soup.find('div', {'id': 'tabset-3'}) 

    current_extract = extract(current_session)
    lifetime_extract = extract(lifetime)

    df_current = pandas.DataFrame.from_records(current_extract)
    df_lifetime = pandas.DataFrame.from_records(lifetime_extract)

    span = "-".join(current_session.span.text.strip('() ').split(' - '))
    soup_to_file(soup, "{span}_NA_Numbers_Ratings.html")
    df_current.to_csv(f'{span}_NA_Numbers_Ratings-Extract.csv', index=False)
    df_lifetime.to_csv(f'{span}_NA_Numbers_Ratings-Extract_lifetime.csv', index=False)


if __name__ == '__main__':
    main()
