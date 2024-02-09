from pathlib import Path
from votervoice import extract, transform, load


def main(url, export_path, *years):
    extracted_by_session = extract.main(url, export_path)
    records_extracted = {i:r for i, r in enumerate(extracted_by_session[next(iter(extracted_by_session))])}
    records_transformed = transform.main(records_extracted, export_path)
    load.main(records_transformed, export_path, *years)


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
    
    main(args.url, args.exportdir, *args.years)
