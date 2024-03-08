import os
from pathlib import Path
from datetime import datetime

# External packages and libraries
import pandas
import psycopg
from rapidfuzz import fuzz
from tqdm import tqdm

from tabular_matcher.matcher import TabularMatcher


def load_query_string(query_filename: Path):
    package_dir = Path(__file__).parent.parent.parent
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


def main(records_transformed: dict[int, dict[str, str]], **module_vars):
    
    assert module_vars.get('VSDB_CONNECTION_INFO') != None #Please provide connection info to VoteSmart's database
    
    print("Connecting...")
    
    conn = psycopg.connect(**module_vars.get("VSDB_CONNECTION_INFO"))
    
    print("Connected to database.")

    query_election_candidates = load_query_string("election_candidates_by_electionyear")
    query_office_list = load_query_string("office_list")

    election_years = {row["election_year"] for row in records_transformed.values()}
    state_names = {row["state_name"] for row in records_transformed.values()}

    records_election_candidates = query_as_records(
        query_election_candidates,
        conn,
        election_years=list(election_years),
        office_ids=list(query_as_reference(query_office_list, conn).values()),
        state_names=list(state_names),
        state_ids=[],
        stages=["G", "P"],
    )

    records_matched = match(records_transformed, records_election_candidates)

    return records_matched, records_election_candidates


if __name__ == "__main__":

    import argparse
    from dotenv import load_dotenv
    
    parser = argparse.ArgumentParser(prog="VoterVoice Load")

    parser.add_argument(
        "-t",
        "--transformed_files",
        type=Path,
        required=True,
        nargs="+",
        help="File containing the scrape extract from votervoice",
    )

    parser.add_argument(
        "-d",
        "--export_dir",
        type=Path,
        required=True,
        help="file directory of where the files exports to",
    )

    load_dotenv()

    args = parser.parse_args()
    db_connection_info = {'host': os.getenv('VSDB_HOST'),
                          'dbname': os.getenv('VSDB_DBNAME'),
                          'port':os.getenv('VSDB_PORT'),
                          'user':os.getenv('VSDB_USER'),
                          'password':os.getenv('VSDB_PASSWORD'),
                        }

    dfs = []
    for file in args.transformed_files:
        dfs.append(
            pandas.read_csv(file, na_values="nan", dtype=str, keep_default_na=False)
        )

    combined_dfs = pandas.concat(dfs, ignore_index=True)
    records_transformed = combined_dfs.to_dict(orient="index")

    records_matched, records_election_candidates = main(records_transformed,
                                                        VSDB_CONNECTION_INFO=db_connection_info)

    timestamp = datetime.strftime(datetime.now(), "%Y-%m-%d-%H%M%S-%f")
    filename_prefix = f"{datetime.strftime(datetime.now(), "%Y")}_NA_NRA_{'{filename}'}"

    df_matched = pandas.DataFrame.from_dict(records_matched, orient="index")
    df_matched.to_csv(
        args.export_dir / f"{filename_prefix.format(filename='Ratings-Matched')}_{timestamp}.csv",
        index=False
    )
    
    df_election_candidates = pandas.DataFrame.from_dict(records_election_candidates, orient="index")
    df_election_candidates.to_csv(
        args.export_dir / f"{filename_prefix.format(filename='VSDB-Candidates')}_{timestamp}.csv",
        index=False
    )
    
