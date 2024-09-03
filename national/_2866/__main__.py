import os
import argparse
from pathlib import Path
from datetime import datetime

import pandas
from dotenv import load_dotenv
from national._2866.extract import main as extract


def transform():
    """Module that transform"""
    pass


def match():
    """Module that matches"""
    pass


FILENAME = f"_NA_FFS_"
YEARS = [str(i) for i in range(2011, 2103)]
CONG_SESSIONS = [
    (s, i) for s in range(112, 112 + int(len(YEARS) / 2)) for i in range(1, 3)
]
YEAR_TO_SESSION = dict(zip(YEARS, CONG_SESSIONS))


def save_records(
    records: dict[int, dict[str, str]],
    filename: str,
    filepath: Path,
    *additional_info,
):

    filepath.mkdir(exist_ok=True)
    timestamp = datetime.strftime(datetime.now(), "%Y-%m-%d-%H%M%S-%f")

    df = pandas.DataFrame.from_dict(records, orient="index")
    df.to_csv(
        filepath
        / (
            f"{filename}_{'-'.join(map(str, additional_info))}"
            f"{'-' if additional_info else ''}{timestamp}.csv"
        ),
        index=False,
    )


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-d",
        "--export_path",
        type=Path,
        required=True,
        help="filepath of the directory where files are exported to",
    )

    parser.add_argument(
        "-f",
        "--file",
        type=Path,
        help="read extracted or transformed file",
    )

    parser.add_argument(
        "-y",
        "--years",
        type=str,
        nargs="+",
        help="Year(s) of the ratings",
    )

    parser.add_argument(
        "-hp",
        "--html_path",
        type=Path,
        help="filepath to HTML directory",
    )

    parser.add_argument(
        "-e",
        "--extract",
        action="store_true",
        help="to extract only",
    )

    parser.add_argument(
        "-t",
        "--transform",
        action="store_true",
        help="to transform only",
    )

    parser.add_argument(
        "-m",
        "--match",
        action="store_true",
        help="to match only",
    )

    args = parser.parse_args()

    load_dotenv()

    vsdb_conn_info = {
        "host": os.getenv("VSDB_HOST"),
        "dbname": os.getenv("VSDB_DBNAME"),
        "port": os.getenv("VSDB_PORT"),
        "user": os.getenv("VSDB_USER"),
        "password": os.getenv("VSDB_PASSWORD"),
    }
    if args.years:
        cong_sessions = [
            YEAR_TO_SESSION.get(y) for y in args.years if y in YEAR_TO_SESSION
        ]
    else:
        current_year = datetime.strftime(datetime.now(), "%Y")
        cong_sessions = (
            [YEAR_TO_SESSION.get(current_year)]
            if current_year in YEAR_TO_SESSION
            else []
        )

    if not any((args.extract, args.transform, args.match)):

        extracted_by_session = extract(
            FILENAME + "Ratings",
            args.export_path,
            cong_sessions,
            args.html_path,
        )

        for congress_session, extracted in extracted_by_session.items():
            records_extracted = dict(enumerate(extracted))
            save_records(
                records_extracted,
                FILENAME + "Ratings-Extract",
                args.export_path / "EXTRACT_FILES",
                congress_session,
            )

        # records_transformed = transform(records_extracted)
        # save_records(
        #     records_transformed,
        #     FILENAME + "Ratings-Transformed",
        #     args.export_path / "TRANSFORMED_FILES",
        # )

        # records_matched, records_election_candidates = match(
        #     records_transformed, vsdb_conn_info
        # )

        # save_records(
        #     records_matched,
        #     FILENAME + "Ratings-Matched",
        #     args.export_path / "MATCHED_FILES",
        # )

        # save_records(
        #     records_election_candidates,
        #     FILENAME + "VSDB-Candidates",
        #     args.export_path / "QUERY_FILES",
        # )

    elif args.extract and not (any((args.transform, args.match))):

        extracted_by_session = extract(
            FILENAME + "Ratings",
            args.export_path,
            cong_sessions,
            args.html_path,
        )

        for congress_session, extracted in extracted_by_session.items():
            records_extracted = dict(enumerate(extracted))
            save_records(
                records_extracted,
                FILENAME + "Ratings-Extract",
                args.export_path / "EXTRACT_FILES",
                congress_session,
            )

    # elif args.transform and not (any((args.extract, args.match))):
    #     if not args.file:
    #         parser.print_help()
    #         parser.error("Please specify the filepath of the spreadsheet.")

    #     df_extracted = pandas.read_csv(args.file)
    #     records_extracted = df_extracted.to_dict(orient="index")

    #     records_transformed = transform(records_extracted)
    #     save_records(
    #         records_transformed,
    #         FILENAME + "Ratings-Transformed",
    #         args.export_path / "TRANSFORMED_FILES",
    #     )

    # elif args.match and not any((args.extract, args.transform)):
    #     if not args.file:
    #         parser.print_help()
    #         parser.error("Please specify the filepath of the spreadsheet.")

    #     df_transformed = pandas.read_csv(
    #         args.file, na_values="nan", keep_default_na=False
    #     )
    #     records_transformed = df_transformed.to_dict(orient="index")

    #     records_matched, records_election_candidates = match(
    #         records_transformed, vsdb_conn_info
    #     )

    #     save_records(
    #         records_matched,
    #         FILENAME + "Ratings-Matched",
    #         args.export_path / "MATCHED_FILES",
    #     )

    #     save_records(
    #         records_election_candidates,
    #         FILENAME + "VSDB-Candidates",
    #         args.export_path / "QUERY_FILES",
    #     )


if __name__ == "__main__":
    main()
