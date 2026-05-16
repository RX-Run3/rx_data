'''
Module holding FCopy class
'''
import shutil
import subprocess

from pathlib                import Path
from dmu.logging.log_store  import LogStore

log=LogStore.add_logger('dmu:fsystem:fcopy')
# ----------------------
class FCopy:
    '''
    Class meant to act as a wrapper to rsync by

    - Checking that the server and local machine are suitable
    - Talking to rsync

    Usage:

    ````python
    from dmu import FCopy

    with FCopy(source='userA@serverA') as fcp
        fcp.copy(source='/home/userA/path/file1', target='/home/userB/path/file1') 
    ````

    Will copy a file given the paths, from one remove server to a local path.
    While:

    ````python
    from dmu import FCopy

    with FCopy(target='userA@serverA') as fcp
        fcp.copy(source='/home/userA/path/file1', target='/home/userB/path/file1') 
    ````

    will copy a local file to a remote server.
    Master control has to be enable for the remove server.

    If no source or target are set, the copy is local, i.e. within the same machine.
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

        self._server      = None
        self._socket_path = None

        self._check_utility(name='rsync')
        self._check_utility(name='ssh'  )
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
    def _open_master_connection(self, server: str) -> None:
        '''
        Parameters
        -------------------
        server: SSH server path, i.e. user@server.example
        '''
        if not server:
            return

        socket_path = f'/tmp/cm-{server}.sock'

        log.debug(f'Opening connection to: {server}')
        subprocess.run([
            'ssh',  '-MNf',
            '-o' ,  'ControlMaster=yes',
            '-o' ,  'ControlPersist=10m',
            '-o' , f'ControlPath={socket_path}',
            server
        ], check=True)

        self._server      = server
        self._socket_path = socket_path
    # ----------------------
    def _close_master_connection(self) -> None:
        if not self._server:
            log.debug('Not connected to any server, not closing connection')
            return

        log.debug(f'Closing connection to server: {self._server}')
        subprocess.run([
            'ssh', '-O', 'exit',
            '-o', f'ControlPath={self._socket_path}',
            self._server,
        ], check=False)
    # ----------------------
    def __enter__(self):
        self._open_master_connection(server=self._source)
        self._open_master_connection(server=self._target)

        return self
    # ----------------------
    def __exit__(self, *args):
        _ = args

        self._close_master_connection()
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
            commands = [
                'rsync',
                '--append-verify',
                '-a',
                '-e',
                f'ssh -o ControlPath={self._socket_path} -o PubkeyAuthentication=yes -o PasswordAuthentication=no', 
                spath, tpath]
        else:
            commands = ['rsync', '--append-verify', '-a', spath, tpath]

        log.debug(' '.join(commands))
        result = subprocess.run(
            commands, 
            check          = False,
            capture_output = True, 
            text           = True)

        if result.returncode != 0:
            log.error(f'Status: {result.returncode}')
            log.error(f'STDERR: {result.stderr}')
            log.error(f'STDOUT: {result.stdout}')
            raise RuntimeError(f'Failed to run: {commands}')

        return True
# ----------------------
