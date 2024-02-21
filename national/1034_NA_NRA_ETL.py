## Built-ins
from pathlib import Path

## Local Packages
from NRA_1034.extract import main as extract
from NRA_1034.transform import main as transform
from NRA_1034.match import main as match


def main(export_directory):
    
    records_extracted = extract(export_directory)
    records_transformed = transform(records_extracted, export_directory)
    match(records_transformed, export_directory)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--export_dir', type=Path, required=True)
    
    args = parser.parse_args()
    main(args.export_dir)