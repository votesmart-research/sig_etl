# This is the webscraping script for Eagle Forum, sig_id=1513

import requests
import pandas

from collections import defaultdict
from bs4 import BeautifulSoup
from tqdm import tqdm


URL = "https://cqrcengage.com/eagleforum"


def extract_candidates(soup):

    interior_content = soup.find('div', {'id':'interiorContent'})
    legislation_name = interior_content.find('span', {'class': 'super'}).text.strip()
    stance = interior_content.find('div', {'class':'stancePanel'}).text.strip()
    legislators = soup.find('section', {'class': 'vote-listing'}).find_all('li')
    
    records = defaultdict(dict)

    for leg in legislators:
        name, *vote = leg.find_all('span')
        records[name.text] = {legislation_name: vote[0].text.strip()}

    return records, {legislation_name: stance}


def translate(votes, methodology):

    positive = ('Yea', 'Proxy Yes')
    negative = ('Nay', 'Proxy No')

    for legislation, sig_stance in methodology.items():

        if legislation in votes.keys():

            vote = votes[legislation]

            if vote in positive:
                votes[legislation] = '+' if sig_stance == 'For' else '-'
            elif vote in negative:
                votes[legislation] = '+' if sig_stance == 'Against' else '-'
            else:
                votes[legislation] = '*'
        else:
            print(votes, legislation)

def download_page(soup, title):
    with open(f"Ratings_{title}.html", 'w') as f:
        f.write(soup.prettify())


def main():

    page_source = requests.get(URL + "/scoreboard").text
    soup = BeautifulSoup(page_source, 'html.parser')

    titles = soup.find('aside', {'class':'list_votes'}).find_all('a')
    urls = list(map(lambda a: a['href'].split(';')[0].strip('.'), titles))

    combined_records = defaultdict(dict)
    methodology = dict()

    for url in tqdm(urls):

        page_source = requests.get(f"{URL}{url}").text
        soup = BeautifulSoup(page_source, 'html.parser')

        records, m = extract_candidates(soup)
        methodology.update(m)

        for name, legislation in records.items():
            combined_records[name].update(legislation) 

        download_page(soup, next(iter(m)))


    for _, votes in combined_records.items():
        translate(votes, methodology)

    df = pandas.DataFrame.from_dict(combined_records, orient='index')
    df.to_csv('_NA_Eagle_Ratings-Extract.csv')


if __name__ == '__main__':
    main()