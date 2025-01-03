import re
import pandas
import numpy
from pathlib import Path


VALUES_TO_REPLACE = {
    "office": {"US House": "U.S. House", "US Senate": "U.S. Senate"},
    "party": {"R": "Republican", "D": "Democratic", "I": "Independent"},
}


def get_name(series: pandas.Series):
    pat_title_name = r"\s\([^)]*\)"
    pat_suffix = (
        r"\,?\s?(?P<suffix>(?:[IVX]{2,3}|Jr\.?|Sr\.?|Dr\.?|Mr\.?|Ms\.?|Mrs\.?|M\.?\s?D\.?)$)"
    )
    pat_middlename = r"\s+(?P<middlename>[A-Z]\.)"
    titles = [
        r"^Rep.\s",
        r"^Sen.\s",
        r"^Minority Leader\s",  
        r"^Majority Leader\s",
        r"^Resident Commissioner\s",
        r"^Speaker\s",
        r"^Delegate\s",
        r"^President\s",
        r"^Senate President\s",
        r"Pro Tempore\s",
    ]

    series_title_name = series.apply(
        lambda x: re.sub(pat_title_name, "", x) if isinstance(x, str) else x
    )
    series_name = series_title_name.replace(titles, "", regex=True)
    series_first_mid_last = series_name.apply(
        lambda x: re.sub(pat_suffix, "", x) if isinstance(x, str) else x
    )
    series_first_last = series_first_mid_last.apply(
        lambda x: re.sub(pat_middlename, "", x) if isinstance(x, str) else x
    )
    series_firstname = series_first_last.apply(lambda x: " ".join(x.split()[0:1]))
    series_middlename = series_first_mid_last.str.extract(pat_middlename)
    series_lastname = series_first_last.apply(lambda x: " ".join(x.split()[1:]))
    series_suffix = series_name.str.extract(pat_suffix)

    return pandas.concat(
        [
            series_firstname.rename("firstname"),
            series_lastname.rename("lastname"),
            series_middlename,
            series_suffix,
        ],
        axis=1,
    )


def get_party_state_district(series: pandas.Series):
    pat_inside_parent = r"\((?P<party>\w+)-(?P<state_id>\w+)-?(?P<district>\w+)?\)"
    delegates = series.str.contains("^Delegate", regex=True)

    df_party_state_district = series.str.extract(pat_inside_parent)
    df_party_state_district["district"] = df_party_state_district["district"].replace(
        r"^0+", "", regex=True
    )

    df_party_state_district.loc[delegates, "district"] = "Delegate"
    return df_party_state_district


def main(records_extracted):
    df = pandas.DataFrame.from_dict(records_extracted, orient="index")

    df_name = get_name(df["info"])
    df_party_state_district = get_party_state_district(df["info"])

    df_transformed = pandas.concat(
        [
            df_name,
            df_party_state_district,
            df["office"],
            df["sig_rating"],
            df["sig_rating"].rename("our_rating"),
        ],
        axis=1,
    )

    df_transformed.replace(VALUES_TO_REPLACE, inplace=True)
    df_transformed.replace(numpy.nan, "", inplace=True)

    records_transformed = df_transformed.to_dict(orient="index")

    return records_transformed
