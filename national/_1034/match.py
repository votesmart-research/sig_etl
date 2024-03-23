from pathlib import Path

# External packages and libraries
import pandas
import psycopg
from rapidfuzz import fuzz
from tqdm import tqdm

from record_matcher.matcher import RecordMatcher


def load_query_string(query_filename: str):
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
    rc_matcher = RecordMatcher()

    rc_matcher.x_records = records_transformed
    rc_matcher.y_records = records_query

    rm_config = rc_matcher.config

    rm_config.scorers_by_column.SCORERS.update(
        {"WRatio": lambda x, y: fuzz.WRatio(str(x.lower()), str(y.lower()))}
    )

    rm_config.scorers_by_column.default = "WRatio"
    rm_config.thresholds_by_column.default = 85

    rm_config.populate()

    rm_config.columns_to_get["candidate_id"] = "candidate_id"

    rm_config.columns_to_group["state_name"] = "state_name"
    del rm_config.columns_to_match["state_name"]

    rm_config.columns_to_match["firstname"] = "nickname", "middlename"

    rm_config.thresholds_by_column["middlename"] = 90
    rm_config.thresholds_by_column["lastname"] = 88
    rm_config.thresholds_by_column["suffix"] = 98
    rm_config.thresholds_by_column["office"] = 95
    rm_config.thresholds_by_column["district"] = 95
    rm_config.thresholds_by_column["party"] = 93

    rc_matcher.required_threshold = 85
    rc_matcher.duplicate_threshold = 3

    p_bar = tqdm(total=len(records_transformed))

    records_matched, match_info = rc_matcher.match(update_func=lambda: p_bar.update(1))

    max_key_length = max(match_info, key=lambda x: len(x)) if match_info else 0
    for k, v in match_info.items():
        print(f"{k.rjust(len(max_key_length)+4)}:", v)

    return records_matched


def main(records_transformed: dict[int, dict[str, str]], db_connection_info):

    print("Connecting to database...")
    conn = psycopg.connect(**db_connection_info)
    print("Connected.")

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
