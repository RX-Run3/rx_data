'''
This module contains the XRootEOS class
'''
from XRootD.client        import FileSystem
from XRootD.client.flags  import DirListFlags, StatInfoFlags
from dmu                  import LogStore

log=LogStore.add_logger('dmu:xroot_eos')
# ----------------------
class XRootEOS:
    '''
    This class is meant to represent an EOS host in order to:

    - List contents
    '''
    # ----------------------
    def __init__(self, host : str) -> None:
        '''
        Parameters
        -------------
        host: Path to EOS instance, e.g. root://eoslhcb.cern.ch
        '''
        self._fs = FileSystem(host)
    # ----------------------
    def glob(self, dir_path : str, ext : str) -> list[str]:
        '''
        Parameters
        ------------
        dir_path: Full path to directory in EOS where globbing should start
        ext     : Extension, e.g. root

        Returns
        ------------
        List of paths in EOS, i.e. PFNs
        '''
        log.debug(f'Logging into: {dir_path}')

        status , dir_list = self._fs.dirlist(dir_path, DirListFlags.STAT)
        if not status.ok:
            raise ValueError(f'Cannot open {dir_path}')

        paths   = []
        objects = dir_list.dirlist
        if not objects:
            return paths

        for entry in objects:
            is_dir = (entry.statinfo.flags & StatInfoFlags.IS_DIR)
            if is_dir:
                paths += self.glob(dir_path=f'{dir_path}/{entry.name}', ext = ext)
                continue

            if entry.name.endswith(f'.{ext}'):
                paths.append(f'{dir_path}/{entry.name}')

        npath = len(paths)
        log.debug(f'Found {npath} paths')

        return paths
# ----------------------
