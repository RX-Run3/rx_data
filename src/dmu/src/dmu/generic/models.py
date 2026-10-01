'''
Module meant to contain code needed to deal with loading of data into
pydantic models
'''

import yaml
import contextlib

from jinja2              import Template
from contextvars         import ContextVar
from importlib.resources import files
from dmu                 import LogStore
from dmu.generic         import hashing
from typing              import Any
from typing              import Self
from pathlib             import Path
from pydantic            import BaseModel, model_validator

log=LogStore.add_logger('dmu:generic:models')

_PACKAGE = ContextVar('_PACKAGE', default = '') 
# --------------------------------------------------
class UnpackerModel(BaseModel, frozen = True):
    '''
    Class meant to allow derived classes to:

    - Load models from paths when the value is a string or path ending with '.yaml'
    - Load data directly from path to file
    '''
    # --------------
    @staticmethod
    def _update_path(path : Path) -> Path:
        '''
        Parameters
        ---------------
        package: Name of data package, relative to which path is used
        path   : Relative path

        Returns
        ---------------
        Full path to `path`, i.e. this method updates relative paths
        '''
        if _PACKAGE.get() == '':
            log.info(f'Not updating path: {path}')
            return path

        pkg_path = str(files(_PACKAGE.get()))

        log.debug(f'Updating path with {pkg_path}')
        full_path = pkg_path / path

        return full_path
    # --------------
    @staticmethod
    def _data_from_path(path : Path) -> dict:
        path = UnpackerModel._update_path(path = path)
        if not path.exists():
            raise ValueError(f'File not found: {path}')

        data = UnpackerModel._load_from_path(path = path)

        return data
    # --------------
    @model_validator(mode='before')
    @classmethod
    def _unpack_paths(cls, data : Any):
        '''
        This method will update data by unpacking yaml file paths
        and inserting the python data in the `data` variable
        '''
        log.debug(20 * '-')
        log.debug(f'At {cls}')
        log.debug(20 * '-')
        if cls._is_unpackable(data):
            log.debug(f'Unpacking directly: {data}')
            path        = Path(data)
            loaded_data = cls._data_from_path(path = path)
            return loaded_data
        else:
            log.debug(f'Not unpacking directly: {data}')

        for field_name in cls.model_fields:
            val : Any = data.get(field_name)

            if not cls._is_unpackable(val):
                log.debug(f'Not unpacking {field_name} = {val}')
                continue
                
            log.debug(f'Unpacking field {field_name}')
            path             = Path(val)
            data[field_name] = cls._data_from_path(path = path)

        return data
    # --------------
    @staticmethod
    def _is_unpackable(val : Any) -> bool:
        '''
        Check if val is a valid yaml path to a config
        that can be made into a config
        '''
        if not isinstance(val, (str, Path)):
            return False

        if str(val).endswith('.yaml'):
            return True

        if str(val).endswith('.yaml.j2'):
            return True

        return False
    # --------------
    @classmethod
    def from_yaml(
        cls, 
        path    : Path | str,
        package : None | str = None) -> Self:
        '''
        Parameters
        ------------------
        path   : Path to yaml file storing configuration
        package: If used, this is the data package with respect to which YAML paths
                 will be found in order to unpack them

        Returns
        ------------------
        Instance of model
        '''
        if package is None:
            path = Path(path)
        else:
            path = Path(str(files(package))) / path

        if not path.exists():
            raise ValueError(f'Cannot find: {path}')

        data = UnpackerModel._load_from_path(path = path)

        if package is None:
            return cls(**data)
        
        with cls.package(name = package):
            return cls(**data)
    # ----------------------
    @staticmethod
    def _load_from_path(path : Path):
        '''
        Parameters
        -------------
        path: Path to file with config, e.g. yaml

        Returns
        -------------
        Data from safe loading
        '''
        text = path.read_text()

        if path.name.endswith('.j2'):
            template : Template = Template(source = text)
            text     = template.render()

        return yaml.safe_load(text)
    # --------------
    def to_yaml(self, path : Path) -> None:
        '''
        Parameters
        ----------------
        path: Path to YAML file where current object will be saved
        '''
        py_data = self.model_dump(mode = 'json')
        ym_data = yaml.safe_dump(data = py_data, indent = 2)
        path.write_text(ym_data)
    # --------------
    @classmethod
    def package(cls, name : str):
        '''
        Parameters
        -------------
        Package: name of package where YAML files will be searched
        '''
        token = _PACKAGE.set(name)

        @contextlib.contextmanager
        def _context():
            try:
                yield
            finally:
                _PACKAGE.reset(token) 

        return _context()
# --------------------------------------------------
class HashableModel(BaseModel, frozen = True):
    '''
    Mixing that makes pydantic models hashable 
    '''
    # -------------------------
    def __hash__(self) -> int:
        string = self.model_dump_json()

        return hashing.hash_object(obj = string, as_int = True)
# --------------------------------------------------
