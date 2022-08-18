# This is the webscraping script for American Energy Alliance (AEA), sig_id=2526

from bs4 import BeautifulSoup
import requests
import pandas


def extract(row):

    return {
        'district': row.find('td', {'class':'districtCell'}).text.strip(),
        'state': row.find('td', {'class':'stateCell'}).text.strip(),
        'name': row.find('td', {'class':'nameCell'}).text.strip(),
        'party': row.find('td', {'class':'partyCell'}).text.strip(),
        'score': row.find('td', {'class':'scoreCell'}).text.strip(),
    }

def main():
    page = requests.get("https://www.americanenergyalliance.org/american-energy-scorecard/?spage=overall")
    soup = BeautifulSoup(page.text, 'html.parser')
    all_rows = soup.find('div', {'class':'membersTable'}).find('tbody').find_all('tr')

    extracted = [extract(r) for r in all_rows]
        
    pandas.DataFrame.from_records(extracted).to_csv('_NA_AEA_Ratings-Extract.csv', index=False)

if __name__ == "__main__":
    main()