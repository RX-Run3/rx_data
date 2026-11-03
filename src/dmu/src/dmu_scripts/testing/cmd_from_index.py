'''
This script will

- Print a JSON string corresponding to a group of pytest tests commands, e.g.

0 : code/test_gen.py::test_gen[0]
1 : code/test_gen.py::test_gen[1]
2 : code/test_gen.py::test_gen[2]
3 : code/test_gen.py::test_gen[3]
'''

import json
import numpy
import random
import argparse
from dmu.testing import pytest_utilities

RNG=random.Random(x=42)
# ----------------------
def _parse_args() -> argparse.Namespace:
    '''
    Parses arguments passed by user

    Returns
    --------------
    Instance of configuration data class, built from arguments
    '''

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-i', '--index' , type=int, help='Index of group')
    parser.add_argument('-n', '--ngroup', type=int, help='Number of groups into which to split')
    parser.add_argument('-p', '--path'  , type=str, help='Path to directory where search for tests will start')

    args = parser.parse_args()

    return args
# ----------------------
def _get_json(args : argparse.Namespace) -> list[str]:
    '''
    Parameters
    -------------
    args: Object storing arguments needed to find tests and split them in groups

    Returns
    -------------
    dictionary mapping index to command, corresponding to a group
    '''
    data    = pytest_utilities.get_tests(path = args.path)
    indexes = list(data)
    indexes.sort()
    RNG.shuffle(x=indexes)

    groups  = numpy.array_split(indexes, args.ngroup)

    array   = groups[args.index]

    return [ val for key, val in data.items() if key in array ]
# ----------------------
def main():
    '''
    Entry point
    '''
    args = _parse_args()
    data = _get_json(args=args)

    with open(f'.commands_{args.index}.json', 'w') as ofile:
        json.dump(data, ofile, indent=2)
# ----------------------
if __name__ == '__main__':
    main()
