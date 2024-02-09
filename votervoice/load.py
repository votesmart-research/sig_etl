import json
from pathlib import Path

import pandas
import psycopg
from rapidfuzz import fuzz
from tqdm import tqdm

if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))

from tabular_matcher.matcher import TabularMatcher


VSDB_REF = {
    "offices": {
        "U.S. House": 5,
        "U.S. Senate": 6,
        "State Assembly": 7,
        "State House": 8,
        "State Senate": 9,
        "Delegate": 390,
    }
}


def connect_to_database():
    PACKAGE_DIR = Path(__file__).parent.parent
    CONNECTION_INFO_FILEPATH = PACKAGE_DIR / "conn_info_psycopg.json"

    with open(CONNECTION_INFO_FILEPATH, "r") as f:
        connection_info = json.load(f)

    return psycopg.connect(**connection_info)


def load_query_string(query_filename: Path):
    PACKAGE_DIR = Path(__file__).parent.parent
    with open(PACKAGE_DIR / "queries" / f"{query_filename}.sql", "r") as f:
        query_string = f.read()

    return query_string


def query_from_database(query: str, connection, **params):
    cursor = connection.cursor()
    cursor.execute(query, params)
    headers = [str(k[0]) for k in cursor.description]
    return {
        index: dict(zip(headers, row)) for index, row in enumerate(cursor.fetchall())
    }


def office_name_to_id(connection):
    pass


def state_name_to_id(connection):
    cursor = connection.cursor()
    cursor.execute(
        """SELECT state.name, state_id 
                      FROM state"""
    )
    return {state_name: state_id for state_name, state_id in cursor.fetchall()}


def match(records_transformed, records_query) -> dict[str, dict]:
    tb_matcher = TabularMatcher()

    tb_matcher.x_records = records_transformed
    tb_matcher.y_records = records_query

    tb_matcher.required_threshold = 75
    tb_matcher.duplicate_threshold = 3

    tb_config = tb_matcher.config

    tb_config.scorers_by_column.SCORERS.update(
        {
            "WRatio": lambda x, y: fuzz.WRatio(x, y),
            "PTRatio": lambda x, y: fuzz.partial_token_ratio(
                str(x).lower(), str(y).lower()
            ),
        }
    )

    tb_config.scorers_by_column.default = "WRatio"
    tb_config.thresholds_by_column.default = 75

    tb_config.populate()

    tb_config.columns_to_get["candidate_id"] = "candidate_id"
    del tb_config.columns_to_match["state_id"]

    tb_config.columns_to_match["firstname"] = "middlename", "nickname"
    tb_config.columns_to_group["state_id"] = "state_id"

    tb_config.thresholds_by_column["firstname"] = 85
    tb_config.thresholds_by_column["middlename"] = 90
    tb_config.thresholds_by_column["lastname"] = 88
    tb_config.thresholds_by_column["suffix"] = 98
    tb_config.thresholds_by_column["office"] = 100
    tb_config.thresholds_by_column["district"] = 95
    tb_config.thresholds_by_column["party"] = 100

    tb_config.scorers_by_column["middlename"] = "PTRatio"

    p_bar = tqdm(total=len(records_transformed))

    records_matched, match_info = tb_matcher.match(update_func=lambda: p_bar.update(1))
    records_matched, match_info = tb_matcher.match()

    max_key_length = max(match_info, key=lambda x: len(x)) if match_info else 0
    for k, v in match_info.items():
        print(f"{k.rjust(len(max_key_length)+4)}:", v)

    return records_matched


def save_matched_results(records_matched: dict[int, dict[str, str]], filepath):
    filepath = Path(filepath) / "MATCHED_FILES"
    filepath.mkdir(exist_ok=True)

    df = pandas.DataFrame.from_dict(records_matched, orient="index")
    df.to_csv(filepath / "Ratings-Worksheet_matched.csv", index=False)


def save_query_results(records_query: dict[int, dict[str, str]], filepath):
    filepath = Path(filepath) / "QUERY_FILES"
    filepath.mkdir(exist_ok=True)

    df = pandas.DataFrame.from_dict(records_query, orient="index")
    df.to_csv(filepath / "query.csv", index=False)


def main(records_transformed: dict[int, dict[str, str]], export_path: Path, *years):
    print("Connecting...")
    conn = connect_to_database()
    print("Connected to database.")

    query_incumbents = load_query_string("office-candidates_by_congstatus")

    offices = {VSDB_REF['offices'].get(r["office"]) for r in records_transformed.values()}
    state_ids = {r["state_id"] for r in records_transformed.values()}

    records_query = query_from_database(
        query_incumbents,
        conn,
        start_date=f"{min(years)}-01-03",
        end_date=f"{max(years)}-01-03",
        office_ids=list(offices),
        state_ids=list(state_ids) if state_ids else get_all_states(conn).values(),
        state_names=[],
    )
    records_matched = match(records_transformed, records_query)

    save_matched_results(records_matched, export_path)
    save_query_results(records_query, export_path)

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

    parser.add_argument(
        "-y",
        "--years",
        type=int,
        nargs="+",
        required=True,
        help="Year(s) of the ratings",
    )

    args = parser.parse_args()

    dfs = []
    for file in args.transformedfiles:
        dfs.append(
            pandas.read_csv(file, na_values="nan", dtype=str, keep_default_na=False)
        )

    combined_dfs = pandas.concat(dfs, ignore_index=True)
    records_transformed = combined_dfs.to_dict(orient="index")

    main(records_transformed, args.exportdir, *args.years)
