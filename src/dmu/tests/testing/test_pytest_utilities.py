'''
This module contains tests for pytest_utilities functionalities
'''

from pathlib     import Path
from dmu.testing import pytest_utilities

# ----------------------
def _create_test(path : Path, name : str) -> str:
    '''
    Parameters
    -------------
    path: Path to directory meant to contain the test
    name: Name of test

    Returns
    -------------

    '''
    if not path.exists():
        path.touch()

    data = path.read_text() if path.exists() else ''
    path.write_text(data = f'{data}\ndef test_{name}():\n    pass')

    return f'{path}::test_{name}' 
# ----------------------
def test_collect(tmp_path : Path):
    '''
    This test tests the collection of tests in a dictionary
    '''
    tests  = ['alpha', 'beta', 'gamma']
    modules= ['one', 'two', 'three']

    strings : list[str] = []
    for test in tests:
        for module in modules:
            value = _create_test(path = tmp_path / f'test_{module}.py', name = test)
            strings.append(value)

    data = pytest_utilities.get_tests(path = tmp_path)

    for val in data.values():
        print(val)
    print('----------')
    for val in strings:
        print(val)

    assert set(strings) == set(data.values())
# ----------------------
