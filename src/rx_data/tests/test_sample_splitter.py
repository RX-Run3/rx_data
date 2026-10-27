'''
Module with tests for SampleSplitter
'''
import pytest

from pathlib     import Path
from rx_common   import Project
from rx_data     import SampleSplitter
from dmu.generic import Mode

def test_simple(tmp_path : Path):
    out_path = tmp_path / 'file.json' 

    # Fail to load missing file
    with pytest.raises(ValueError):
        spt = SampleSplitter(
            version = 'v1',
            project = Project.rk)

        files = spt.run(out_path = out_path, mode = Mode.read)

    # Make file
    spt = SampleSplitter(
        version = 'v1',
        project = Project.rk)

    files = spt.run(out_path = out_path, mode = Mode.write)

    assert out_path.exists()

    batches = files.split(entries = 1000_000)

    print(batches)
    print(batches.nentries - files.size)

    assert batches.nentries == files.size

    # Cannot write, file already there
    with pytest.raises(ValueError):
        spt = SampleSplitter(
            version = 'v1',
            project = Project.rk)

        files = spt.run(out_path = out_path, mode = Mode.write)
