'''
Module holding tests for Tunnel class
'''
import os
import time
import pytest
import subprocess

from typing      import Final
from pathlib     import Path
from dmu.fsystem import Tunnel
from dmu         import LogStore 

log = LogStore.add_logger('dmu:test_tunnel')
_SOCKET : Final[Path] = Path('/tmp/test_socket')
_USER   : Final[str]  = os.environ['USER']
# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    process = subprocess.Popen(
        ['ssh', '-M', '-S', str(_SOCKET), '-N', f'{_USER}@localhost']
    )
    for _ in range(10):
        if _SOCKET.exists():
            break

        time.sleep(0.5)
    yield

    process.terminate()
    process.wait()
# ----------------------
@pytest.mark.parametrize('socket', [_SOCKET, None])
def test_glob(
    socket   : Path,
    tmp_path : Path):
    '''
    Test glob 
    '''
    f1 = tmp_path / 'file_1'
    f1.touch()

    f2 = tmp_path / 'file_2'
    f2.touch()

    tnl   = Tunnel(socket = socket)
    paths = tnl.glob(
        path    = tmp_path, 
        pattern = 'file_*')

    assert len(paths) == 2

    assert paths[0] == f1
    assert paths[1] == f2
# ----------------------

