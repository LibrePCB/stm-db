import argparse
import csv
import json
from os import makedirs, path


def _makedir(dirpath: str) -> None:
    """
    Helper function to ensure that a directory exists.
    """
    if not (path.exists(dirpath) and path.isdir(dirpath)):
        makedirs(dirpath)


def should_use(row: dict) -> bool:
    return row['Marketing Status'] == 'Active'


def main(args):
    _makedir('data')

    # Load raw data
    raw_data = []
    with open(args.csv, 'r') as f:
        # Skip first three lines containing garbage
        for _ in range(3):
            f.readline()
        # Load rest of data
        for row in csv.DictReader(f):
            raw_data.append(row)

    # Write CubeMX script
    print('Writing cubemx_script.txt...')
    with open('cubemx_script.txt', 'w') as script:
        script.write('rm -r out/')
        for row in raw_data:
            if not should_use(row):
                continue
            reference = row['Reference']
            script.write('load {}\n'.format(reference))
            script.write('csv pinout data/{}.pinout.csv\n'.format(reference))
        script.write('exit\n')

    # Write info file
    for row in raw_data:
        if not should_use(row):
            continue
        filename = 'data/{}.info.json'.format(row['Reference'])
        print('Writing {}...'.format(filename))
        with open(filename, 'w') as f:
            info = {
                'part_no': row['Part No'],
                'package': row['Package'],
                'boards': [board.strip() for board in row['Board'].split(',') if board.strip()],
                'flash': row['Flash'],
                'ram': row['RAM'],
                'io': row['IO'],
                'frequency': row['Freq.'],
            }
            f.write(json.dumps(info))

    print('Done.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process the base.csv file')
    parser.add_argument(
        '--csv', metavar='path-to-base.csv', required=True,
        help='path to the base.csv file',
    )
    args = parser.parse_args()
    main(args)
