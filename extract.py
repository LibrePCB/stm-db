import argparse
import json
import sqlite3
import zipfile
from os import makedirs, path
from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET


class CubeFinderDbPart:
    """
    Class representing a part from the Cube Finder Database
    """
    def __init__(self, mpn: str, t_min: Optional[float], t_max: Optional[float],
                 packing_type: Optional[str], status: Optional[str]):
        self.mpn = mpn
        self.t_min = t_min
        self.t_max = t_max
        self.packing_type = packing_type
        self.status = status

    def to_json(self) -> dict:
        """
        Generate the JSON data to be included in generated files
        """
        return dict(
            mpn=self.mpn,
            temperature_min=self.t_min,
            temperature_max=self.t_max,
            packing_type=self.packing_type,
            status=self.status,
        )


class CubeFinderDb:
    """
    Helper class to extract information from ST's Cube Finder Database
    """
    def __init__(self, db_file: str):
        self._db = sqlite3.connect(db_file)
        self._cur = self._db.cursor()

    def get_parts_for_ref(self, ref: str) -> List[str]:
        """
        Get a list of all parts for a given MCU ref
        """
        res = self._cur.execute(
            "SELECT id, cpn FROM cpn WHERE refname = :refname",
            dict(refname=ref),
        )
        return [
            CubeFinderDbPart(
                mpn=row[1],
                t_min=self._get_attribute(row[0], 'temperatureMin', is_num=True),
                t_max=self._get_attribute(row[0], 'temperatureMax', is_num=True),
                packing_type=self._get_attribute(row[0], 'packing_type'),
                status=self._get_attribute(row[0], 'marketingStatus'),
            )
            for row in res.fetchall()
        ]

    def _get_attribute(self, cpn_id: int, attribute_name: str,
                       is_num: bool = False) -> str:
        """
        Extract a specific attribute of a given cpn_id
        """
        res = self._cur.execute(
            "SELECT strValue, numValue FROM cpn_has_attribute "
            "LEFT JOIN attribute "
            "ON attribute.id = cpn_has_attribute.attribute_id "
            "WHERE cpn_id = :cpn_id "
            "AND attribute.name = :attribute_name",
            dict(
                cpn_id=cpn_id,
                attribute_name=attribute_name,
            ),
        ).fetchone()
        if res is not None:
            return res[1 if is_num else 0]
        else:
            return None


def _makedir(dirpath: str) -> None:
    """
    Helper function to ensure that a directory exists.
    """
    if not (path.exists(dirpath) and path.isdir(dirpath)):
        makedirs(dirpath)


def main(args):
    _makedir('data')
    _makedir('tmp')

    # Extract MCU Finder SQLite database into the local directory and load it.
    cube_finder_zip = path.join(args.db, 'plugins', 'mcufinder', 'mcu', 'cube-finder-db.zip')
    with zipfile.ZipFile(cube_finder_zip, 'r') as f:
        f.extract('cube-finder-db.db', 'tmp')
    db = CubeFinderDb('tmp/cube-finder-db.db')

    with open(path.join(args.db, 'mcu', 'families.xml'), 'r') as f:
        tree = ET.parse(f)
        families = tree.getroot()
        assert families.tag == 'Families'
        for family in families:
            print('Processing family {}'.format(family.get('Name')))
            for subfamily in family:
                print(' Processing subfamily {}'.format(subfamily.get('Name')))
                for mcu in subfamily:
                    print('  Processing MCU {}'.format(mcu.get('Name')))
                    process_mcu(args, db, mcu.get('Name'), mcu.get('RefName'), mcu.get('RPN'))


def process_mcu(args, db: CubeFinderDb, name: str, ref: str, rpn: str):
    """
    Fetch pinout information for this MCU and write it to the data dir.
    """
    with open(path.join(args.db, 'mcu', '{}.xml'.format(name)), 'r') as f:
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
            'silicon': {},
            'info': {
                'flash': int(mcu.find('{*}Flash').text),  # type: ignore
                'ram': int(mcu.find('{*}Ram').text),  # type: ignore
                'io': int(mcu.find('{*}IONb').text),  # type: ignore
            },
            'parts': [part.to_json() for part in db.get_parts_for_ref(ref)],
        }  # type: Dict[str, Any]
        if mcu.find('{*}Core') is not None:
            data['silicon']['core'] = mcu.find('{*}Core').text  # type: ignore
        if mcu.find('{*}Die') is not None:
            data['silicon']['die'] = mcu.find('{*}Die').text  # type: ignore
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
                'variant': pin.get('Variant'),
                'signals': [signal.get('Name') for signal in pin.iterfind('{*}Signal')],
            })

        with open(path.join('data', '{}.json'.format(ref)), 'w') as f:
            f.write(json.dumps(data, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process the base.csv file')
    parser.add_argument(
        '--db', metavar='path-to-cubemx-db-mcu-dir', required=True,
        help='path to the STM32CubeMX database directory',
    )

    args = parser.parse_args()
    main(args)
