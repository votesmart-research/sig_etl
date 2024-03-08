from pathlib import Path
from datetime import datetime

from votervoice import extract, match, transform

import pandas


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


def main(url, export_path, years):
    extracted_by_session = extract.main(url, export_path)
    sessions = list(extracted_by_session.keys())

    for session in sessions:
        for year in years:
            if session and session in extracted_by_session and str(year) in session:
                records_extracted = dict(enumerate(extracted_by_session.pop(session)))
                save_records(
                    records_extracted,
                    "Ratings-Extract",
                    export_path / "EXTRACT_FILES",
                    session,
                )

                records_transformed = transform.main(records_extracted)
                save_records(
                    records_transformed,
                    "Ratings-Transformed",
                    export_path / "TRANSFORMED_FILES",
                    session,
                )

                records_matched, records_query = match.main(records_transformed, years)

                save_records(
                    records_matched,
                    "Ratings-Matched",
                    export_path / "MATCHED_FILES",
                    session,
                )
                save_records(
                    records_query,
                    "VSDB-Candidates",
                    export_path / "QUERY_FILES",
                    session,
                )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(prog="votervoice_scrape")
    parser.add_argument(
        "-u",
        "--url",
        type=str,
        required=True,
        help="website url where the ratings are located",
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

    main(args.url, args.export_path, args.years)
