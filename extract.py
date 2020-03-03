import argparse
import json
from os import makedirs, path
from typing import Any, Dict
import xml.etree.ElementTree as ET


def _makedir(dirpath: str) -> None:
    """
    Helper function to ensure that a directory exists.
    """
    if not (path.exists(dirpath) and path.isdir(dirpath)):
        makedirs(dirpath)


def main(args):
    _makedir('data')

    with open(path.join(args.db, 'families.xml'), 'r') as f:
        tree = ET.parse(f)
        families = tree.getroot()
        assert families.tag == 'Families'
        for family in families:
            print('Processing family {}'.format(family.get('Name')))
            for subfamily in family:
                print(' Processing subfamily {}'.format(subfamily.get('Name')))
                for mcu in subfamily:
                    print('  Processing MCU {}'.format(mcu.get('Name')))
                    process_mcu(args, mcu.get('Name'), mcu.get('RefName'), mcu.get('RPN'))


def process_mcu(args, name: str, ref: str, rpn: str):
    """
    Fetch pinout information for this MCU and write it to the data dir.
    """
    with open(path.join(args.db, '{}.xml'.format(name)), 'r') as f:
        tree = ET.parse(f)
        mcu = tree.getroot()
        assert mcu.tag.endswith('Mcu'), mcu.tag
        data = {
            'names': {
                'name': name,
                'ref': ref,
                'family': mcu.get('Family'),
                'line': mcu.get('Line'),
                'rpn': rpn,
            },
            'package': mcu.get('Package'),
            'info': {
                'flash': int(mcu.find('{*}Flash').text),  # type: ignore
                'ram': int(mcu.find('{*}Ram').text),  # type: ignore
                'io': int(mcu.find('{*}IONb').text),  # type: ignore
            },
        }  # type: Dict[str, Any]
        if mcu.find('{*}E2prom') is not None:
            data['info']['eeprom'] = int(mcu.find('{*}E2prom').text)  # type: ignore
        if mcu.find('{*}Frequency') is not None:
            data['info']['frequency'] = int(mcu.find('{*}Frequency').text)  # type: ignore
        if mcu.find('{*}Voltage') is not None:
            data['info']['voltage'] = {
                'min': float(mcu.find('{*}Voltage').get('Min')),  # type: ignore
                'max': float(mcu.find('{*}Voltage').get('Max')),  # type: ignore
            }
        if mcu.find('{*}Temperature') is not None:
            temp_min = mcu.find('{*}Temperature').get('Min')  # type: ignore
            temp_max = mcu.find('{*}Temperature').get('Max')  # type: ignore
            if temp_min is not None and temp_max is not None:
                data['info']['temperature'] = {
                    'min': float(temp_min),
                    'max': float(temp_max),
                }

        data['gpio_version'] = mcu.find('./{*}IP[@Name="GPIO"]').get('Version')  # type: ignore
        data['pinout'] = []
        for pin in mcu.iterfind('{*}Pin'):
            data['pinout'].append({
                'name': pin.get('Name'),
                'position': pin.get('Position'),
                'type': pin.get('Type'),
                'signals': [signal.get('Name') for signal in pin.iterfind('{*}Signal')],
            })

        with open(path.join('data', '{}.json'.format(ref)), 'w') as f:
            f.write(json.dumps(data, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process the base.csv file')
    parser.add_argument(
        '--db', metavar='path-to-cubemx-db-mcu-dir', required=True,
        help='path to the mcu directory in the STM32CubeMX database',
    )

    args = parser.parse_args()
    main(args)
