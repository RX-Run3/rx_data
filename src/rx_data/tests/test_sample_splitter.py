'''
Module with tests for SampleSplitter
'''

from pathlib   import Path
from rx_common import Project
from rx_data   import SampleSplitter


def test_simple():
    spt = SampleSplitter(
        version = 'v1',
        project = Project.rk)

    fname = Path('files.json')
    files = spt.run(out_path = '/tmp' / fname)
    print(files.size)
