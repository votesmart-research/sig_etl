import os
from pathlib import Path

import psycopg
from rapidfuzz import fuzz
from tqdm import tqdm
from dotenv import load_dotenv

from tabular_matcher.matcher import TabularMatcher


def load_query_string(query_filename: Path):
    package_dir = Path(__file__).parent.parent
    filepath = package_dir / "queries" / f"{query_filename}.sql"

    with open(filepath, "r") as f:
        query_string = f.read()

    return query_string


def query_as_records(query: str, connection, **params):
    cursor = connection.cursor()
    cursor.execute(query, params)

    headers = [str(k[0]) for k in cursor.description]
    return {
        index: dict(zip(headers, row)) for index, row in enumerate(cursor.fetchall())
    }


def query_as_reference(query: str, connection, **params):
    cursor = connection.cursor()
    cursor.execute(query, params)
    return {name: ids for ids, name in cursor.fetchall()}


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


def main(records_transformed: dict[int, dict[str, str]], years):
    
    load_dotenv()

    db_connection_info = {
        "host": os.getenv("VSDB_HOST"),
        "dbname": os.getenv("VSDB_DBNAME"),
        "port": os.getenv("VSDB_PORT"),
        "user": os.getenv("VSDB_USER"),
        "password": os.getenv("VSDB_PASSWORD"),
    }

    print("Connecting...")
    conn = psycopg.connect(**db_connection_info)
    print("Connected to database.")

    query_incumbents = load_query_string("office-candidates_by_congstatus")
    query_offices = load_query_string("office_list")
    office_list = query_as_reference(query_offices, conn)

    office_ids = {
        office_list.get(r["office"])
        for r in records_transformed.values()
        if r["office"] in office_list
    }
    state_ids = {r["state_id"] for r in records_transformed.values()}

    records_query = query_as_records(
        query_incumbents,
        conn,
        start_date=f"{min(years)}-01-03",
        end_date=f"{max(years)}-01-03",
        office_ids=list(office_ids),
        state_ids=list(state_ids),
        state_names=[],
    )
    records_matched = match(records_transformed, records_query)

    return records_matched, records_query


if __name__ == "__main__":
    import argparse
    import pandas

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
        "--export_path",
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

    records_matched, records_query = main(
        records_transformed, args.exportdir, *args.years
    )

    df_matched = pandas.DataFrame.from_dict(records_matched, orient="index")
    df_query = pandas.DataFrame.from_dict(records_query, orient="index")

    df_matched.to_csv(args.export_path / "Ratings-Matched.csv", index=False)
    df_query.to_csv(args.export_path / "VSDB-Candidates.csv", index=False)
