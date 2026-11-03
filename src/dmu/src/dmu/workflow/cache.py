'''
This module contains
'''
import os
import sys
import shutil

from pathlib    import Path
from contextlib import contextmanager
from typing     import Any

from dmu.generic           import hashing
from dmu.logging.log_store import LogStore

log=LogStore.add_logger('dmu:workflow:cache')
# ---------------------------
class Cache:
    '''
    Class meant to wrap other classes in order to

    - Keep track of the inputs through hashes
    - Load cached data, if found, and prevent calculations

    The following directories will be important:

    out_dir  : Directory where the outputs will go, specified by the user
    cache_dir: Subdirectory of out_dir, ${out_dir}/.cache
    hash_dir : Subdirectory of out_dir, ${out_dir}/.cache/{hash}
               Where {hash} is a 10 alphanumeric representing the has of the inputs

    # On skipping caching

    This is controlled by `_l_skip_class` which is a list of class names:

    - These classes will have the caching turned off
    - If the list is empty, caching runs for everything
    - If the list is None, caching is turned off for everything
    '''
    _cache_root     : Path     | None = None
    _l_skip_class   : list[str]| None = []
    # ---------------------------
    def __init__(self, out_path : Path, **kwargs : Any):
        '''
        Parameters
        ---------------
        out_path: Path where outputs will go, it can be relative to _cache_root or not
        kwargs  : Key word arguments symbolizing identity of inputs, used for hashing
                  If code = True, code will be used to build hash
                  If code = False or code is not among the arguments, it won't be used
        '''
        if Cache._cache_root is None:
            raise ValueError('Caching directory not set')

        log.debug(f'Using {Cache._cache_root} root directory for caching')
        if 'code' in kwargs and kwargs['code']:
            kwargs['code']  = self._get_code_hash()
        else:
            log.debug('Not using code for hashing')

        # If user uses absolute path, respect that
        # If relative path, make it relative to _cache_root
        if   out_path.is_absolute():
            self._out_path = out_path
        else:
            self._out_path = Cache._cache_root / out_path

        log.debug(f'Using {self._out_path} output path')
        self._out_path.mkdir(parents=True, exist_ok=True)

        self._hsh       = hashing.hash_object(kwargs, as_int = False)
        self._cache_dir = self._get_dir(kind='cache')
    # ---------------------------
    def _get_code_hash(self) -> str:
        '''
        If `MyTool` inherits from `Cache`. `mytool.py` git commit hash
        should be returned
        '''
        cls   = self.__class__
        mod   = sys.modules.get(cls.__module__)
        if mod is None:
            raise ValueError(f'Module not found: {cls.__module__}')

        if mod.__file__ is None:
            raise ValueError(f'Cannot extract file path for module: {cls.__module__}')

        fname = mod.__file__
        fpath = os.path.abspath(fname)
        val   = hashing.hash_file(path=fpath)

        log.debug(f'Using hash for: {fpath} = {val}')

        return val
    # ---------------------------
    def _get_dir(
        self,
        kind : str,
        make : bool = True) -> Path:
        '''
        Parameters
        --------------
        kind : Kind of directory, cash, hash
        make : If True (default) will try to make directory
        '''
        if   kind == 'cache':
            dir_path  = self._out_path / '.cache'
        elif kind == 'hash':
            cache_dir = self._get_dir(kind='cache')
            dir_path  = cache_dir / self._hsh
        else:
            raise ValueError(f'Invalid directory kind: {kind}')

        if make:
            dir_path.mkdir(parents=True, exist_ok=True)

        return dir_path
    # ---------------------------
    def _cache(self) -> None:
        '''
        Meant to be called after all the calculations finish
        It will copy all the outputs of the processing
        to a hashed directory
        '''
        hash_dir  = self._get_dir(kind= 'hash')
        log.info(f'Caching outputs to: {hash_dir}')

        for source in self._out_path.glob('*'):
            if source == self._cache_dir:
                continue

            log.debug(str(source))
            log.debug('-->')
            log.debug(hash_dir)
            log.debug('')

            if source.is_dir():
                shutil.copytree(source, hash_dir / source.name, dirs_exist_ok=True)
            else:
                shutil.copy2(source, hash_dir)

        self._delete_from_output()
        self._copy_from_hashdir(hash_dir = hash_dir)
    # ---------------------------
    def _delete_from_output(self) -> None:
        '''
        Deletes all objects from _out_path directory, except for `.cache`
        '''
        for path in self._out_path.iterdir():
            if path == self._cache_dir:
                log.debug(f'Skipping cache dir: {self._cache_dir}')
                continue

            log.debug(f'Deleting {path}')
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            else:
                path.unlink()
    # ---------------------------
    def _copy_from_hashdir(self, hash_dir : Path) -> None:
        '''
        Copies all the objects from hash_dir to _out_path
        '''
        for source in hash_dir.iterdir():
            target = self._out_path / source.name
            log.debug(f'{str(source):<50}{"-->"}{target}')

            os.symlink(source, target)
    # ---------------------------
    def _dont_cache(self) -> bool:
        '''
        Returns
        ---------------
        Flag that if:

        True : Will stop the derived class from using caching (i.e. caching is off)
        False: Cache
        '''
        if Cache._l_skip_class is None:
            log.info('No class will be cached')
            return True

        if len(Cache._l_skip_class) == 0:
            log.debug('All classes will be cached')
            return False

        class_name = self.__class__.__name__

        skip = class_name in Cache._l_skip_class

        if skip:
            log.warning(f'Caching turned off for {class_name}')
        else:
            log.debug(f'Caching turned on  for {class_name}')

        return skip
    # ---------------------------
    def _copy_from_cache(self) -> bool:
        '''
        Checks if hash directory exists:

        No : Returns False
        Yes:
            - Removes contents of `out_path`, except for .cache
            - Copies the contents of `hash_dir` to `out_dir`

        Returns
        ---------------
        True if the object, cached was found, false otherwise.
        '''
        if self._dont_cache():
            # If not copying from cache, will need to remove what is
            # in the output directory, so that it gets replaced with
            # new outputs
            self._delete_from_output()
            log.info('Not picking already cached outputs, remaking them')
            return False

        hash_dir = self._get_dir(kind='hash', make=False)
        if not os.path.isdir(hash_dir):
            log.info(f'Hash directory {hash_dir} not found, not caching')
            self._delete_from_output()
            return False

        log.debug(f'Data found in hash directory: {hash_dir}')

        self._delete_from_output()
        self._copy_from_hashdir(hash_dir = hash_dir)

        return True
    # ---------------------------
    @classmethod
    def get_cache_dir(cls) -> Path:
        '''
        Returns path to directory where outputs are stored
        '''
        if cls._cache_root is None:
            raise ValueError('Cache directory is not set')

        return cls._cache_root
    # ---------------------------
    @property
    def path(self) -> Path:
        '''
        Path to directory where objects are cached
        '''
        return self._out_path
    # ---------------------------
    @property
    def hash(self):
        '''
        String with hash associated to dataset
        '''
        return self._hsh
    # ---------------------------
    @classmethod
    def turn_off_cache(cls, val : list[str] | None):
        '''
        Parameters
        ------------------
        val: List of names of classes that inherit from `Cache`.
        If None, will not cache for any class.
        By default this is an empty list and it will cache for every class
        '''
        old_val = cls._l_skip_class
        @contextmanager
        def _context():
            cls._l_skip_class = val
            try:
                yield
            finally:
                cls._l_skip_class = old_val

        return _context()
    # ---------------------------
    @classmethod
    def cache_root(cls, path : Path):
        '''
        Context manager used to set caching directory

        Parameters
        ----------------
        path: Path to directory where outputs will be cached
        '''
        old_val = cls._cache_root
        @contextmanager
        def _context():
            cls._cache_root = path
            try:
                yield
            finally:
                cls._cache_root = old_val

        return _context()
    # ---------------------------
    @classmethod
    def set_cache_root(cls, root : Path) -> None:
        '''
        Sets the path to the directory WRT which the _out_path_
        will be placed.

        This is meant to be called once per execution and has a lock
        that will raise an exception if called twice
        '''
        if cls._cache_root is not None:
            raise ValueError(f'Trying to set {root}, but already found {cls._cache_root}')

        root.mkdir(parents = True, exist_ok = True)

        cls._cache_root = root
# ---------------------------
