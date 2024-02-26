import os
from pathlib import Path
from datetime import datetime
from NRA_1034.extract import main as extract
from NRA_1034.transform import main as transform
from NRA_1034.match import main as match


import pandas
from dotenv import load_dotenv


URL = "https://www.nrapvf.org"
PDF_OLD_PREFIX = "NRA-PVF _ Grades _ "
FILENAME_PREFIX = f"{datetime.strftime(datetime.now(), "%Y")}_NA_NRA_{'{filename}'}"


def save_records(
    records: dict[int, dict[str, str]],
    filename: str,
    filepath: Path,
    *additional_info,
):

    filepath.mkdir(exist_ok=True)
    timestamp = datetime.strftime(datetime.now(), "%Y-%m-%d-%H%M%S-%f")

    df = pandas.DataFrame.from_dict(records, orient="index")
    df.to_csv(filepath / (f"{filename}_{'-'.join(map(str, additional_info))}"
                          f"{'-' if additional_info else ''}{timestamp}.csv"),
              index=False
    )


def main(export_directory):
    
    load_dotenv()

    records_extracted = extract(URL,
                                PDF_OLD_PREFIX = PDF_OLD_PREFIX,
                                FILENAME_PREFIX = FILENAME_PREFIX,
                                EXPORT_DIR = export_directory,
                                )
    
    save_records(records_extracted, 
                 FILENAME_PREFIX.format(filename='Ratings-Extract'),
                 export_directory / "EXTRACT_FILES")
    
    records_transformed = transform(records_extracted)
    
    save_records(records_transformed,
                 FILENAME_PREFIX.format(filename='Ratings-Transformed'),
                 export_directory / "TRANSFORMED_FILES")
    
    vsdb_conn_info = {'host': os.getenv('VSDB_HOST'),
                      'dbname': os.getenv('VSDB_DBNAME'),
                      'port':os.getenv('VSDB_PORT'),
                      'user':os.getenv('VSDB_USER'),
                      'password':os.getenv('VSDB_PASSWORD'),
                    }
    
    records_matched, records_election_candidates = match(records_transformed, 
                                                         VSDB_CONNECTION_INFO=vsdb_conn_info)
    
    save_records(records_matched,
                 FILENAME_PREFIX.format(filename='Ratings-Matched'),
                 export_directory / "MATCHED_FILES")
    
    save_records(records_election_candidates,
                 FILENAME_PREFIX.format(filename='VSDB-Candidates'),
                 export_directory / "QUERY_FILES")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--export_dir', type=Path, required=True)
    
    args = parser.parse_args()
    main(args.export_dir)