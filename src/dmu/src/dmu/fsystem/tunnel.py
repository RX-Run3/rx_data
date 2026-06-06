'''
Module holding the Tunnel class
'''
import subprocess

from pathlib import Path

# -----------------------------
class Tunnel:
    '''
    Class meant to allow access to file systems through a socket
    '''
    # -----------------------------
    def __init__(self, socket : Path | None):
        '''
        Parameters
        ---------------
        socket: Path to socket or None if running over local filesystem
        '''
        if socket and not socket.exists():
            raise FileNotFoundError(f'Cannot find socket: {socket}')

        self._socket = socket
    # -----------------------------
    def run(self, cmd : str) -> int:
        '''
        Parameters
        ---------------
        cmd: Command to run in server, e.g. `ls *.txt`
        '''
        if self._socket:
            args = ['ssh', '-S', self._socket, 'x', cmd]
        else:
            args = ['bash', '-c', cmd]

        result = subprocess.run(
            args, 
            capture_output = True,
            check          = True,
            text           = True)

        if result.returncode != 0:
            raise RuntimeError(result.stderr)

        return result.stdout
    # -----------------------------
    def glob(
        self, 
        path    : Path, 
        pattern : str) -> list[Path]:
        '''
        Parameters
        --------------
        path: Path to directory to be globed
        pattern: e.g. *.root 

        Returns
        --------------
        List of paths in filesystem 
        '''
        text  = self.run(f'ls {path}/{pattern}')
        lines = text.splitlines()
        paths = [ Path(line) for line in lines ]

        return paths
# -----------------------------
