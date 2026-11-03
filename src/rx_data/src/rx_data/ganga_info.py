'''
Module with the GangaInfo class
'''
import os
import re
import tarfile

from contextlib import contextmanager
from getpass    import getuser
from pathlib    import Path
from typing     import Final

from dmu.generic           import hashing
from dmu.generic           import utilities as gut
from dmu.logging.log_store import LogStore

log=LogStore.add_logger('rx_data:ganga_info')
# -------------------------------
class GangaInfo:
    '''
    This class is meant to:

    - Look for Ganga sandbox
    - Read from exe-script.py and Script1_Ganga_Executable.log mapping between
      sample names and block information
    - Make them available to the user
    '''
    user = getuser()

    CACHE_DIR : Final[Path] = Path(f'/tmp/{user}/cache/ganga_info')
    MC_BK_RGX : Final[str ] = r'(w\d{2}_\d{2})_v\dr\d{4}'
    DT_BK_RGX : Final[str ] = r'\'(data_turbo_2\dc\d)\''
    OFILE_RGX : Final[str ] = r'\'((?:data|mc)_\w*\.root)\''
    # ----------------------
    def __init__(self, job_ids : list[int]) -> None:
        '''
        Parameters
        -------------
        job_ids: List of Ganga job IDs where search will happen
        '''
        self._ganga_dir : Path          = Path(os.environ['GANGADIR'])
        self._data      : dict[str,str] = self._load_data(job_ids=job_ids)

        GangaInfo.CACHE_DIR.mkdir(exist_ok=True)
    # ----------------------
    def _load_data(self, job_ids : list[int]) -> dict[str,str]:
        '''
        Parameters
        -------------
        job_ids: List of integers representing job ganga IDs

        Returns
        -------------
        dictionary with:

        Key  : ROOT file name
        Value: Block information
        '''
        if len(job_ids) == 0:
            raise ValueError('Empty job IDs list passed')

        hash_obj = self._ganga_dir, job_ids
        val      = hashing.hash_object(hash_obj)
        opath    = GangaInfo.CACHE_DIR/f'{val}.json'
        if opath.is_file():
            log.info(f'Loading from: {opath}')
            data = gut.load_json(path=opath)
            return data

        data : dict[str,str] = {}
        for job_id in job_ids:
            info = self._info_from_job_id(job_id=job_id)
            data.update(info)

        if len(data) == 0:
            raise ValueError('Empty filename -> block container')

        log.info(f'Caching to: {opath}')
        gut.dump_json(data=data, path=opath)

        return data
    # ----------------------
    def _info_from_job_id(self, job_id : int) -> dict[str,str]:
        '''
        Parameters
        -------------
        job_id: Ganga job ID

        Returns
        -------------
        dictionary with:

        Key  : ROOT file name
        Value: Block information
        '''
        job_dir : Path         = self._ganga_dir/f'{job_id}'
        l_subjob_dir           = job_dir.glob('*')
        d_data : dict[str,str] = {}

        for subjob_dir in l_subjob_dir:
            subjob : str = subjob_dir.name
            if not subjob.isdigit():
                continue

            out_fname = subjob_dir/'output/Script1_Ganga_Executable.log'
            tar_fname = subjob_dir/f'input/_input_sandbox_{job_id}_{subjob}.tgz'
            inp_fname = self._file_from_tarball(tar_fpath=tar_fname)

            if not out_fname.is_file():
                log.info(f'Cannot find output for job: {job_id}/{subjob}')
                continue

            log.debug('')
            log.debug(f'Searching: {subjob_dir}')
            info : dict[str,str] = self._info_from_logs(
                input_path =inp_fname,
                output=out_fname)

            d_data.update(info)

        return d_data
    # ----------------------
    def _info_from_logs(self, input_path : Path, output : Path) -> dict[str,str]:
        '''
        Parameters
        -------------
        input: Path to exe-script.py file
        output: Path to log file with job output information

        Returns
        -------------
        dictionary with:

        Key  : sample name
        Value: block information
        '''
        block    = self._block_from_input(path=input_path)
        l_sample = self._samples_from_output(path=output)

        log.debug(f'Block: {block}')
        log.debug(f'Samples: {l_sample}')

        return { sample : block for sample in l_sample }
    # ----------------------
    def _samples_from_output(self, path : Path) -> list[str]:
        '''
        Parameters
        -------------
        path: Path to log file with job output information

        Returns
        -------------
        List of ROOT file names produced by job
        '''
        with open(path, 'r') as ifile:
            lines = ifile.readlines()

        try:
            [line] = [ line for line in lines if 'files on WN:' in line ]
        except ValueError as exc:
            raise ValueError(f'Cannot find list of outputs in log: {path}') from exc

        # Many jobs have no output files
        mtch = re.search(GangaInfo.OFILE_RGX, line)
        if not mtch:
            log.debug(f'Missing file names in {line}')
            return []

        t_group = mtch.groups()
        if isinstance(t_group, tuple) and all(isinstance(x, str) for x in t_group):
            return list(t_group)

        raise ValueError(f'Returned list of output files is not a list: {t_group}')
    # ----------------------
    def _block_from_input(self, path : Path) -> str:
        '''
        Parameters
        -------------
        input: Path to exe-script.py file

        Returns
        -------------
        block information
        '''
        with open(path, 'r') as ifile:
            lines = ifile.readlines()

        l_cmd    = [ line for line in lines if 'execmd' in line ]
        cmd_line = l_cmd[0]

        mtch     = re.search(GangaInfo.MC_BK_RGX, cmd_line)
        if mtch:
            return mtch.group(1)

        mtch     = re.search(GangaInfo.DT_BK_RGX, cmd_line)
        if mtch:
            return mtch.group(1)

        raise ValueError(f'Cannot find block information in: {cmd_line}')
    # ----------------------
    def _file_from_tarball(self, tar_fpath : Path) -> Path:
        '''
        Parameters
        -------------
        tar_fpath: Path to tarball containing input files

        Returns
        -------------
        Path to input file, after opening tarball.
        This should go to a caching directory
        in order not to pullute the ganga sandbox
        '''
        untar_dir = GangaInfo.CACHE_DIR/'input_logs'/tar_fpath.name.replace('.tgz', '')
        untar_dir.mkdir(exist_ok=True, parents=True)

        inp_file = untar_dir/'exe-script.py'
        if inp_file.is_file():
            log.debug(f'Input file already found: {inp_file}')
            return inp_file

        with tarfile.open(tar_fpath, 'r:gz') as tar:
            tar.extractall(path=untar_dir)

        if not untar_dir.is_dir():
            raise FileNotFoundError(f'Cannot untar {tar_fpath} into {untar_dir}')

        if not inp_file.is_file():
            raise FileNotFoundError(f'Cannot find exe-script.py in: {untar_dir}')

        return inp_file
    # ----------------------
    @property
    def ganga_dir(self) -> Path:
        '''
        Returns
        --------------
        Path to Ganga sandbox directory
        '''
        if self._ganga_dir is None:
            raise ValueError('Ganga directory not defined')

        return self._ganga_dir
    # ----------------------
    def block_from_fname(self, fname : str, fallback : str|None = None) -> str:
        '''
        Parameters
        -------------
        fname   : Name of ROOT file produced by filtering step
        fallback: If specified, will use that value for file names without blocks

        Returns
        -------------
        block identifier, e.g. w40_42
        '''
        if fname not in self._data:
            if fallback is not None:
                return fallback

            for key, val in self._data.items():
                log.info(f'{key:<30}{val}')

            raise ValueError(f'File {fname} not found')

        return self._data[fname]
    # ----------------------
    @classmethod
    def set_ganga_dir(cls, directory : Path|str):
        '''
        This is a context manager meant to override the value of
        GANGADIR, which is the location of the sandbox, i.e. the
        directory where the numbered directory jobs are located.

        Parameters
        -------------
        dir: Directory path for Ganga sandbox
        '''
        if isinstance(directory, str):
            directory = Path(directory)

        if not directory.is_dir():
            raise FileNotFoundError(f'Non-existent path: {directory}')

        old_dir = os.environ.get('GANGADIR')

        @contextmanager
        def _context():
            try:
                os.environ['GANGADIR'] = str(directory)
                yield
            finally:
                if old_dir is None:
                    os.environ.pop('GANGADIR', None)
                else:
                    os.environ['GANGADIR'] = old_dir

        return _context()
# ----------------------
