'''
Module holding SampleSplitter class
'''
import os

from dmu       import LogStore
from typing    import Final
from pathlib   import Path
from ROOT      import RDataFrame
from rx_common import Project
from pydantic  import BaseModel, RootModel, model_validator

_ANADIR   : Final[Path] = Path(os.environ['ANADIR'])
_TREE     : Final[str ] = 'main'
_OUT_PATH : Final[Path] = Path('.samples.json')
_TREE_NAME: Final[str]  = 'DecayTree'

log=LogStore.add_logger('rx_data:sample_splitter')
# ------------------------------------
class FilePart(BaseModel):
    '''
    Class representing part of ROOT file
    '''
    path : Path
    range: tuple[int,int]
# ------------------------------------
class File(BaseModel):
    '''
    Object representing ROOT file
    '''
    path    : Path
    entries : int
    # ------------------------------------
    @model_validator(mode = 'before')
    @classmethod
    def _validate(cls, data) -> 'File':
        path = Path(data['path'])

        if not path.exists():
            raise ValueError(f'Missing file: {path}')

        rdf      = RDataFrame(_TREE_NAME, str(path))
        nentries = rdf.Count().GetValue()

        data['entries'] = nentries 

        return data 
    # ------------------------------------
    def parts(self, entries : int) -> list[FilePart]:
        '''
        Parameters
        ----------------
        entries: Maximum number of entries in file part

        Returns
        ----------------
        List of objects representing file partitioning
        '''
        file_parts = []
        for start in range(0, self.entries + 1, entries):
            end = min(start + entries - 1, self.entries)

            element  = FilePart(
                path = self.path,
                range= (start, end))

            file_parts.append(element)

        return file_parts
# ------------------------------------
class Files(RootModel[list[File]]):
    '''
    Represents list of files
    '''
    # ------------------------------------
    @classmethod
    def from_json(cls, path : Path) -> 'Files':
        text = path.read_text()
        return cls.model_validate_json(text)
    # ------------------------------------
    def split(self, entries : int) -> list[FilePart]:
        '''
        Parameters
        -------------
        entries: Maximum number of entries allowed in part

        Returns
        -------------
        List of objects representing file parts
        '''
        parts : list[FilePart] = []
        for file in self.root:
            parts += file.parts(entries = entries)

        return parts
# ------------------------------------
class SampleSplitter:
    '''
    Class meant to create database
    with statistics associated to project samples
    '''
    # ------------------------------------
    def __init__(
        self, 
        project : Project,
        version : str):
        '''
        Parameters
        ------------
        project: E.g. rk
        version: Version of files
        '''
        self._project = project
        self._version = version
    # ------------------------------------
    def _get_files(self) -> Files:
        '''
        Returns
        ---------------
        List of object representing ROOT files
        '''
        dir_path = _ANADIR / 'Data' / self._project / _TREE / self._version
        paths    = list(dir_path.glob(pattern = '*.root'))
        if not paths:
            raise ValueError(f'No ROOT file found in {dir_path}')

        return Files([ File(path = path, entries = 0) for path in paths ])
    # ------------------------------------
    def run(self, out_path : Path | None = None) -> Files:
        '''
        Runs creation of database
        '''
        if not out_path:
            out_path = _OUT_PATH

        if out_path.exists():
            log.info(f'Found cached: {out_path}')
            return Files.from_json(path = out_path)

        log.info(f'Not found cached, caching: {out_path}')
        files  = self._get_files()
        string = files.model_dump_json(indent = 2)

        out_path.write_text(string)

        return files
# ------------------------------------
