'''
Module holding FCopy class
'''
import shutil
import subprocess

from pathlib               import Path
from dmu.logging.log_store import LogStore

log=LogStore.add_logger('dmu:fsystem:fcopy')
# ----------------------
class FCopy:
    '''
    Class meant to act as a wrapper to rsync by

    - Checking that the server and local machine are suitable
    - Talking to rsync

    Usage:

    ````
    from dmu import FCopy

    fcp = FCopy(source='userA@serverA', target='userB@serverB')
    fcp.copy(source='/home/userA/path/file1', target='/home/userB/path/file1') 
    ````

    Will copy a file given the paths, from one server to another.

    The connection must be possible without passwords, i.e. with key pairs
    By default source and target in initializer are empty strings and the
    files are assumed to be local
    '''
    # ----------------------
    def __init__(
        self, 
        source : str = '', 
        target : str = '',
        timeout: int = 50):
        '''
        Parameters
        -------------
        source : User and server name where input files are, e.g. user@server.ch
        target : User and server name where output files will go, e.g. user@server.ch
        timeout: When checking for servers availability, wait this number of seconds
        
        If server and/or target are left empty (default), the files will be assumed to be local
        '''
        if source and target:
            raise RuntimeError('Source and target cannot be both remote')

        self._source = source
        self._target = target 
        self._timeout= timeout

        self._check_utility(name='rsync')
        self._check_utility(name='ssh'  )
        self._check_remote(server=self._source)
        self._check_remote(server=self._target)
    # ----------------------
    def _check_remote(self, server : str) -> None:
        '''
        Parameters
        -------------
        path   : String representing server, if empty, its local
        timeout: Number of seconds to wait when accessing server
        '''
        if not server:
            return

        try:
            result = subprocess.run(
                ['ssh', '-o', f'ConnectTimeout={self._timeout}', 
                 '-o', 'BatchMode=yes',
                 '-o', 'PubkeyAuthentication=yes',
                 '-o', 'PasswordAuthentication=no',
                 '-o', 'StrictHostKeyChecking=no', server, 
                 '/bin/true'],
                capture_output= True,
                check         = False,
                timeout       = self._timeout)
        except subprocess.TimeoutExpired as exc:
            raise ValueError(f'Timeout, cannot access: {server}') from exc

        code = result.returncode
        if code != 0:
            log.info(result.stdout)
            log.error(result.stderr)

            raise ValueError(f'Error {code}, cannot access: {server}')
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
    def _get_path(self, path : Path, is_source : bool) -> str:
        '''
        Parameters
        -------------
        path     : Path in server, e.g. /home/user/file.p
        is_source: If true, this is where the file will be copied from

        Returns
        -------------
        String with full path to server or local
        '''
        if not self._source and not self._target:
            return str(path)

        if     is_source and not self._source:
            if not path.exists():
                raise FileNotFoundError(f'Source \"{path}\" missing')

            return str(path)

        if not is_source and not self._target:
            return str(path)

        if is_source:
            return f'{self._source}:{path}'
        else:
            return f'{self._target}:{path}'
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

        spath = self._get_path(source, is_source= True)
        tpath = self._get_path(target, is_source=False)

        if self._source or self._target:
            commands = ['rsync', '--append-verify', '-a', '-e', 'ssh -o PubkeyAuthentication=yes -o PasswordAuthentication=no', spath, tpath]
        else:
            commands = ['rsync', '--append-verify', '-a', spath, tpath]

        log.debug(' '.join(commands))
        result = subprocess.run(commands, capture_output = True, text = True)

        if result.returncode != 0:
            log.error(f'Status: {result.returncode}')
            log.error(f'STDERR: {result.stderr}')
            log.error(f'STDOUT: {result.stdout}')
            raise RuntimeError(f'Failed to run: {commands}')

        return True
# ----------------------
