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
    pat_suffix = r"(?P<suffix>[IVX][IVX]+$|[DJMS][rs][s]?[\.]+|[M]\.?\s?[D]\.?\s?)"
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
    df_party_state_district["district"].replace(r"^0+", "", inplace=True, regex=True)
    
    df_party_state_district.loc[delegates, "district"] = "Delegate"
    return df_party_state_district


def save_transformed(records_transformed: dict[int, dict[str, str]], filepath):
    filepath = Path(filepath) / "TRANSFORMED_FILES"
    filepath.mkdir(exist_ok=True)

    df = pandas.DataFrame.from_dict(records_transformed, orient="index")
    df.to_csv(filepath / "Ratings-Worksheet_transformed.csv", index=False)


def main(records_extracted, export_path: Path):
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
    df_transformed.replace(numpy.NaN, '', inplace=True)
    
    records_transformed = df_transformed.to_dict(orient="index")
    save_transformed(records_transformed, export_path)

    return records_transformed


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(prog="VoterVoice Transform")

    parser.add_argument(
        "-e",
        "--extractfiles",
        type=Path,
        required=True,
        nargs="+",
        help="File containing the scrape extract from votervoice",
    )

    parser.add_argument(
        "-d",
        "--exportdir",
        type=Path,
        required=True,
        help="File directory of where transformed files exports to",
    )

    args = parser.parse_args()

    dfs = []

    for file in args.extractfiles:
        dfs.append(pandas.read_csv(file))

    combined_dfs = pandas.concat(dfs, ignore_index=True)
    records_extracted = combined_dfs.to_dict(orient="index")

    main(records_extracted, args.exportdir)
