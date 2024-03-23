import argparse
from pathlib import Path
from datetime import datetime

from votervoice.extract import main as extract
from votervoice.transform import main as transform
from votervoice.match import main as match

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


def main():

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
        help="Year(s) of the ratings",
    )

    parser.add_argument(
        "-f",
        "--file",
        type=Path,
    )

    parser.add_argument(
        "-e",
        "--extract",
        action="store_true",
    )

    parser.add_argument(
        "-t",
        "--transform",
        action="store_true",
    )

    parser.add_argument(
        "-m",
        "--match",
        action="store_true",
    )

    args = parser.parse_args()

    if not any((args.extract, args.transform, args.match)):

        if not args.years:
            parser.print_help()
            parser.error("Please specify the years")

        extracted_by_session = extract(args.url, args.export_path)
        sessions = list(extracted_by_session)

        for session in sessions:
            for year in args.years:
                if session and session in extracted_by_session and str(year) in session:
                    # popping session would prevent it from reiterating
                    records_extracted = dict(
                        enumerate(extracted_by_session.pop(session))
                    )
                    save_records(
                        records_extracted,
                        "Ratings-Extract",
                        args.export_path / "EXTRACT_FILES",
                        session,
                    )

                    records_transformed = transform(records_extracted)

                    save_records(
                        records_transformed,
                        "Ratings-Transformed",
                        args.export_path / "TRANSFORMED_FILES",
                        session,
                    )

                    records_matched, records_query = match(
                        records_transformed, args.years
                    )

                    save_records(
                        records_matched,
                        "Ratings-Matched",
                        args.export_path / "MATCHED_FILES",
                        session,
                    )
                    save_records(
                        records_query,
                        "VSDB-Candidates",
                        args.export_path / "QUERY_FILES",
                        session,
                    )

    elif args.extract and not (any((args.transform, args.match))):

        extracted_by_session = extract(args.url, args.export_path)
        sessions = list(extracted_by_session)
        records_to_extract = {}

        if args.years:
            for session in sessions:
                for year in args.years:
                    if (
                        session
                        and session in extracted_by_session
                        and str(year) in session
                    ):
                        # popping session would prevent it from reiterating
                        records_to_extract[session] = dict(
                            enumerate(extracted_by_session.pop(session))
                        )
        else:
            if extracted_by_session:
                latest_session = list(extracted_by_session)[0]
                records_to_extract[latest_session] = dict(
                    enumerate(extracted_by_session[latest_session])
                )

        for session, records_extracted in records_to_extract.items():
            save_records(
                records_extracted,
                "Ratings-Extract",
                args.export_path / "EXTRACT_FILES",
                session,
            )

    elif args.transform and not (any((args.extract, args.match))):

        if not args.file:
            parser.print_help()
            parser.error("Please specify the filepath of the spreadsheet.")

        df_extracted = pandas.read_csv(args.file)
        records_extracted = df_extracted.to_dict(orient="index")

        records_transformed = transform(records_extracted)

        save_records(
            records_transformed,
            "Ratings-Transformed",
            args.export_path / "TRANSFORMED_FILES",
            " ".join(args.file.name.split("_")[-1].split("-")[:-5]),
        )

    elif args.match and not any((args.extract, args.transform)):

        if not args.file:
            parser.print_help()
            parser.error("Please specify the filepath of the spreadsheet.")

        if not args.years:
            parser.print_help()
            parser.error("Please specify the years")

        df_transformed = pandas.read_csv(
            args.file, na_values="nan", keep_default_na=False
        )
        records_transformed = df_transformed.to_dict(orient="index")
        records_matched, records_query = match(records_transformed, args.years)

        save_records(
            records_matched,
            "Ratings-Matched",
            args.export_path / "MATCHED_FILES",
            " ".join(args.file.name.split("_")[-1].split("-")[:-5]),
        )
        save_records(
            records_query,
            "VSDB-Candidates",
            args.export_path / "QUERY_FILES",
            " ".join(args.file.name.split("_")[-1].split("-")[:-5]),
        )


if __name__ == "__main__":
    main()
