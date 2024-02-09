## Built-ins
from pathlib import Path

## Local Packages
from NRA_1034.extract import main as extract
from NRA_1034.transform import main as transform
from NRA_1034.load import main as load


def main(export_directory):
    
    records_extracted = extract(export_directory)
    records_transformed = transform(records_extracted, export_directory)
    load(records_transformed, export_directory)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--exportdir', type=Path, required=True)
    
    args = parser.parse_args()
    main(args.exportdir)