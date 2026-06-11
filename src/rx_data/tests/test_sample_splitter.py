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

    fname   = Path('files.json')
    files   = spt.run(out_path = '/tmp' / fname)
    batches = files.split(entries = 1000_000)

    print(batches)
    print(batches.nentries - files.size)

    assert batches.nentries == files.size

