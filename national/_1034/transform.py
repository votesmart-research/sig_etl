import re
from datetime import datetime

# External packages and libraries
import pandas
from unidecode import unidecode


VALUES_TO_REPLACE = {
    "party": {
        "A": "Alaskan Independent",
        "AI": "American Independent",
        "C": "Conservative",
        "D": "Democratic",
        "DFL": "Democratic/Farmer/Labor",
        "D-NPL": "Democratic-NPL",
        "G": "Green Party",
        "I": "Independent",
        "I/D": "Unaffiliated",
        "IND. R": "Independent Republican",
        "IR": "Independent Republican",
        "L": "Libertarian",
        "N": "No Party Affiliation",
        "NP": "Non-partisan",
        "NPA": "No Party Affiliation",
        "WI": "Write-In",
        "P&F": "Peace and Freedom",
        "PAF": "Peace and Freedom",
        "R": "Republican",
        "SPP": "Seattle People's Party",
        "U": "Undeclared",
        "V": "Veterans",
        "?": "Unknown",
    },
    "office": {
        "Commissioner of Agriculture": "Agriculture Commissioner",
        "Lt. Governor": "Lieutenant Governor",
        "Lt.Governor": "Lieutenant Governor",
        "State Treasurer": "Treasurer",
        "US House": "U.S. House",
        "US Senate": "U.S. Senate",
        "General Assembly": "State Assembly",
        "House": "State House",
        "House of Representative": "State House",
        "House of Delegates": "State House",
        "HOUSE OF REPRESENTATIVES": "State House",
        "State Attorney": "Attorney General",
        "State House of Delegates": "State House",
        "State House of Representatives": "State House",
        "Tax Collector": "Commissioner",
    },
}


def transform_split(df: pandas.DataFrame):

    df_1 = df[df["candidate_grade"].str.contains("/") == True]

    if not df_1.any:
        return df

    split_candidate_name = (
        df_1["candidate_name"].str.split("/", expand=True).stack().reset_index()
    )
    split_candidate_grade = (
        df_1["candidate_grade"].str.split("/", expand=True).stack().reset_index()
    )
    split_candidate_office = (
        df_1["election_location"].str.split("/", expand=True).stack().reset_index()
    )

    df_2 = pandas.concat([df_1] * 2).sort_index()
    df_2.reset_index(inplace=True)

    df_3 = pandas.concat(
        [
            split_candidate_name[0].rename("candidate_name"),
            split_candidate_grade[0].rename("candidate_grade"),
            df_2["candidate_endorsed"],
            df_2["candidate_status"],
            split_candidate_office[0].rename("election_location"),
            df_2["election_type"],
            df_2["election_date"],
            df_2["state"],
            df_2["collected"],
        ],
        axis=1,
    )

    df.drop(index=df_1.index, inplace=True)

    return pandas.concat([df, df_3], ignore_index=True)


def transform_name(series: pandas.Series):

    pat_nickname = r"[\"\'\(](?P<nickname>.*?)[\"\'\)]"
    pat_suffix = (
        r"\,?\s?(?P<suffix>(?:[IVX]{2,3}|Jr\.?|Sr\.?|Dr\.?|Mr\.?|Ms\.?|Mrs\.?)$)"
    )
    pat_middlename = r"(?<![A-Z][a-z]\.)|(?:\s)(?P<middlename>(?:[A-Z]{1}\.?))(?=\s|$)"

    def clean_name(name):
        name = re.sub(pat_nickname, "", name)
        # Replace suffix before middlename because it succeeds middlename
        name = re.sub(pat_suffix, "", name)
        name = re.sub(pat_middlename, "", name)
        return name.strip()

    series = series.apply(unidecode)

    series_first_last = series.apply(clean_name)

    rows_w_comma = series_first_last.apply(lambda x: "," in x)

    series_firstname = series_first_last[~rows_w_comma].apply(
        lambda x: " ".join(x.split()[0:-1])
    )
    series_lastname = series_first_last[~rows_w_comma].apply(lambda x: x.split()[-1])

    series_comma_lastname = series_first_last[rows_w_comma].apply(
        lambda x: x.split(",")[0]
    )
    series_comma_firstname = series_first_last[rows_w_comma].apply(
        lambda x: x.split(",")[-1]
    )

    combined_firstname = series_firstname.combine_first(series_comma_firstname)
    combined_lastname = series_lastname.combine_first(series_comma_lastname)

    df_nickname = series.str.extract(pat_nickname)
    df_suffix = series.str.extract(pat_suffix)
    df_middlename = series.str.extract(pat_middlename)

    return pandas.concat(
        [
            combined_firstname.rename("firstname"),
            combined_lastname.rename("lastname"),
            df_nickname,
            df_suffix,
            df_middlename,
        ],
        axis=1,
    )


def transform_candidate_status(series: pandas.Series):

    split_candidate_status = series.str.split("(", expand=True)

    series_status = split_candidate_status[0]
    series_party = split_candidate_status[1].apply(lambda x: x.strip(")"))

    return pandas.concat(
        [series_status.rename("status"), series_party.rename("party")], axis=1
    )


def transform_election_location(series: pandas.Series):

    split_location = series.str.split(" - ", expand=True)

    pat_district = r"(^.*)(?=District.*)(.*$)"
    pat_office = r".*\d+.*"

    df_district = pandas.concat(
        [
            split_location[i].str.extract(pat_district, flags=re.IGNORECASE).dropna()
            for i in split_location.keys()[1:]
        ]
    )

    series_office = split_location[0].str.replace(pat_office, "", regex=True)
    series_district = df_district[[0, 1]].agg("".join, axis=1).reindex()

    words_to_remove = ["District", "Congressional", "Senatorial", r"\(.*\)"]
    sub_pattern_remove = "|".join([rf"(\s?{word}\s?)" for word in words_to_remove])

    series_district.replace(sub_pattern_remove, value="", regex=True, inplace=True)

    return pandas.concat(
        [series_office.rename("office"), series_district.rename("district")], axis=1
    )


def transform_election_date(series: pandas.Series):

    split_election_date = series.str.split(",", expand=True)

    def verify_date(x):
        try:
            return datetime.strptime(x, "%B %d,%Y").strftime("%Y-%m-%d")

        except ValueError:
            return None

    series_election_year = split_election_date.iloc[:, -1].str.strip()
    series_election_monthday = split_election_date.iloc[:, -2].str.strip()
    series_election_date = (
        series_election_monthday + "," + series_election_year
    ).apply(lambda x: verify_date(x))

    return pandas.concat(
        [
            series_election_year.rename("election_year"),
            series_election_date.rename("election_date"),
        ],
        axis=1,
    )


def main(records_extracted: dict[int, dict[str, str]], **module_vars):

    df = pandas.DataFrame.from_dict(records_extracted, orient="index")

    df = transform_split(df)
    df_name = transform_name(df["candidate_name"])
    df_candidate_status = transform_candidate_status(df["candidate_status"])
    df_election_location = transform_election_location(df["election_location"])
    df_election_date = transform_election_date(df["election_date"])

    df_transformed = pandas.concat(
        [
            df_name["firstname"].str.strip(),
            df_name["middlename"].str.strip(),
            df_name["lastname"].str.strip().str.strip(","),
            df_name["suffix"].str.strip(),
            df_name["nickname"].str.strip(),
            df_candidate_status["status"].str.strip(),
            df_election_date["election_year"],
            df["election_type"].str.strip(),
            df["state"].rename("state_name").str.strip(),
            df_election_location["office"].str.strip("-").str.strip(),
            df_election_location["district"].str.strip(),
            df_candidate_status["party"].str.strip(),
            df["candidate_grade"].str.strip(),
            df["candidate_endorsed"],
            df_election_date["election_date"],
            df["collected"],
        ],
        axis=1,
    )

    df_transformed.replace(VALUES_TO_REPLACE, inplace=True)

    records_transformed = (
        df_transformed.astype(str).replace("nan", "").to_dict(orient="index")
    )

    return records_transformed
