## Built-ins
import json
from pathlib import Path
from datetime import datetime

## External packages and libraries
import pandas
import psycopg
from rapidfuzz import fuzz
from tqdm import tqdm

PACKAGE_DIR = Path(__file__).parent.parent

if __name__ == "__main__":
    import sys
    sys.path.insert(0, PACKAGE_DIR)
    sys.path.insert(1, PACKAGE_DIR.parent)
    sys.path.insert(2, PACKAGE_DIR.parent.parent)
    print(sys.path)
    
from tabular_matcher.matcher import TabularMatcher

YEAR = datetime.strftime(datetime.now(), "%Y")
TIMESTAMP = datetime.strftime(datetime.now(), "%Y-%m-%d-%H%M")
FILENAME = (
    f"{YEAR}_NA_NRA_Ratings{'{filetype}'}_{'{additional_info}'}{TIMESTAMP}.{'{ext}'}"
)

PACKAGE_DIR = Path(__file__).parent.parent

def connect_to_database():
    PACKAGE_DIR = Path(__file__).parent.parent
    CONNECTION_INFO_FILEPATH = PACKAGE_DIR / "conn_info_psycopg.json"
    
    if not CONNECTION_INFO_FILEPATH.exists():
        PACKAGE_DIR = PACKAGE_DIR.parent
        CONNECTION_INFO_FILEPATH = PACKAGE_DIR / "conn_info_psycopg.json"
        print(CONNECTION_INFO_FILEPATH)

    with open(CONNECTION_INFO_FILEPATH, "r") as f:
        connection_info = json.load(f)       

    return psycopg.connect(**connection_info)


def load_query_string(query_filename: Path):
    PACKAGE_DIR = Path(__file__).parent.parent
    
    filepath = PACKAGE_DIR / "queries" / f"{query_filename}.sql"
    
    if not filepath.exists():
        PACKAGE_DIR = PACKAGE_DIR.parent
        filepath = PACKAGE_DIR / "queries" / f"{query_filename}.sql"
    
    with open(filepath, "r") as f:
        query_string = f.read()

    return query_string


def query_from_database(query: str, connection, **params):
    cursor = connection.cursor()
    cursor.execute(query, params)
    headers = [str(k[0]) for k in cursor.description]
    return {
        index: dict(zip(headers, row)) for index, row in enumerate(cursor.fetchall())
    }


def get_all_offices(connection):
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT office_id, office.name
        FROM office
        ORDER BY rank ASC
    """
    )
    return {office_name: office_id for office_id, office_name in cursor.fetchall()}


def match(records_transformed: pandas.DataFrame, records_query: pandas.DataFrame):
    tb_matcher = TabularMatcher()

    tb_matcher.x_records = records_transformed
    tb_matcher.y_records = records_query

    tb_config = tb_matcher.config

    tb_config.scorers_by_column.SCORERS.update(
        {"WRatio": lambda x, y: fuzz.WRatio(x, y)}
    )

    tb_config.scorers_by_column.default = "WRatio"
    tb_config.thresholds_by_column.default = 85

    tb_config.populate()

    tb_config.columns_to_get["candidate_id"] = "candidate_id"

    tb_config.columns_to_group["state_name"] = "state_name"
    del tb_config.columns_to_match["state_name"]

    tb_config.columns_to_match["firstname"] = "nickname", "middlename"

    tb_config.thresholds_by_column["middlename"] = 90
    tb_config.thresholds_by_column["lastname"] = 88
    tb_config.thresholds_by_column["suffix"] = 98
    tb_config.thresholds_by_column["office"] = 95
    tb_config.thresholds_by_column["district"] = 95
    tb_config.thresholds_by_column["party"] = 93

    tb_matcher.required_threshold = 85
    tb_matcher.duplicate_threshold = 3

    p_bar = tqdm(total=len(records_transformed))

    records_matched, match_info = tb_matcher.match(update_func=lambda: p_bar.update(1))

    max_key_length = max(match_info, key=lambda x: len(x)) if match_info else 0
    for k, v in match_info.items():
        print(f"{k.rjust(len(max_key_length)+4)}:", v)

    return records_matched


def save_records(
    records_queried: dict[int, dict[str, str]], filetype: str, filepath: Path
):

    filepath.mkdir(exist_ok=True)

    filename = FILENAME.format(filetype=filetype, additional_info="", ext=".csv")

    df = pandas.DataFrame.from_dict(records_queried, orient="index")
    df.to_csv(filepath / filename, index=False)


def quote_join(l):
    return ", ".join(map(lambda x: f"'{x}'", l))


def main(records_transformed: dict[int, dict[str, str]], export_directory: Path):
    print("Connecting...")
    conn = connect_to_database()
    print("Connected to database.")

    query_election_candidates = load_query_string("election_candidates_by_electionyear")

    election_years = {row["election_year"] for row in records_transformed.values()}
    state_names = {row["state_name"] for row in records_transformed.values()}

    records_query = query_from_database(
        query_election_candidates,
        conn,
        election_years=list(election_years),
        office_ids=list(get_all_offices(conn).values()),
        state_names=list(state_names),
        state_ids=[],
        stages=['G', 'P']
    )

    records_matched = match(records_transformed, records_query)

    ## Export files
    save_records(records_query, "Query", filepath=export_directory / "QUERY_FILES")
    save_records(
        records_matched, "Matched", filepath=export_directory / "MATCHED_FILES"
    )

    return records_matched, records_query


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(prog="VoterVoice Load")

    parser.add_argument(
        "-t",
        "--transformedfiles",
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
        help="file directory of where the files exports to",
    )

    args = parser.parse_args()

    dfs = []
    for file in args.transformedfiles:
        dfs.append(
            pandas.read_csv(file, na_values="nan", dtype=str, keep_default_na=False)
        )

    combined_dfs = pandas.concat(dfs, ignore_index=True)
    records_transformed = combined_dfs.to_dict(orient="index")

    main(records_transformed, args.exportdir)
