'''
Module holding FCopy class
'''
import re
import shutil
import subprocess

from pathlib                import Path
from dmu.logging.log_store  import LogStore

log=LogStore.add_logger('dmu:fsystem:fcopy')
# ----------------------
class FCopy:
    '''
    Class meant to act as a wrapper to rsync by

    - Checking that the server is reachable
    - Talking to rsync

    ````python
    from dmu import FCopy

    with FCopy(target='-p 1234 userA@serverA') as fcp
        fcp.copy(source='/home/userA/path/file1', target='/home/userB/path/file1')
    ````

    will copy a local file to a remote server.
    User has to setup reverse forwarding from target server to local one with

    ssh -R xxxx:localhost:xxxx user@lxlogin.ihep.ac.cn

    Such that this class can use port xxx to connect to target
    machine through localhost
    '''
    # ----------------------
    def __init__(
        self,
        server : str,
        timeout: int = 50):
        '''
        Parameters
        -------------
        target : User and server name where output files will go, e.g. -p 1234 user@server.ch
        timeout: When checking for servers availability, wait this number of seconds

        If server and/or target are left empty (default), the files will be assumed to be local
        '''
        port, login  = self._read_server(server = server)
        self._port   = port
        self._login  = login
        self._timeout= timeout

        self._check_utility(name='rsync')
        self._check_utility(name='ssh'  )

        self._close_on_exit = False
    # ----------------------
    def _read_server(self, server : str) -> tuple[str,str]:
        '''
        Parameters
        -------------
        server: E.g. -p 1234 user@server

        Returns
        -------------
        Tuple with port number and server, e.g.

        1234, user@server
        '''
        REGEX = r'-p\s+(\d+)\s+(.*)'
        match = re.match(REGEX, server)

        if not match:
            raise ValueError(f'Cannot extract port and sever from: {server}')

        return match.group(1), match.group(2)
    # ----------------------
    def _check_utility(self, name : str) -> None:
        '''
        Check if utility is available

        Parameters
        ----------------
        name: Name of utility, e.g. rsync
        '''
        path = shutil.which(name)
        if path is None:
            raise ValueError(f'Utility \"{name}\" not found')

        log.debug(f'Utility \"{name}\" found at: {path}')
    # ----------------------
    def copy(self, source : Path, target : Path) -> bool:
        '''
        Parameters
        ---------------
        source: Path to file to be copied
        target: Destination path

        Returns
        ---------------
        True if success
        '''
        log.debug('')
        log.debug(source)
        log.debug('--->')
        log.debug(target)

        commands = [
            'rsync',
            '--mkpath',
            '--progress',
            '--append-verify',
            '-a',
            '-e',
            f'ssh -p {self._port}', str(source), f'{self._login}:{target}']

        log.debug(' '.join(commands))
        result = subprocess.run(
            commands,
            check = False,
            stderr=subprocess.PIPE,
            text  = True)

        if result.returncode != 0:
            log.error(f'Status: {result.returncode}')
            log.error(f'STDERR: {result.stderr}')
            raise RuntimeError(f'Failed to run: {commands}')

        return True
# ----------------------
