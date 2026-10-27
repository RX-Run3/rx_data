'''
Module with tests for SampleSplitter
'''

from pathlib     import Path
from rx_common   import Project
from rx_data     import SampleSplitter
from dmu.generic import Mode

def test_simple(tmp_path : Path):
    spt = SampleSplitter(
        version = 'v1',
        project = Project.rk)

    fname   = Path('files.json')
    files   = spt.run(out_path = tmp_path / fname, mode = Mode.write)
    batches = files.split(entries = 1000_000)

    print(batches)
    print(batches.nentries - files.size)

    assert batches.nentries == files.size
