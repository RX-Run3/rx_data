'''
Module holding SampleSplitter class and other helper classes
'''
import os

from dmu       import LogStore
from typing    import Final, Any
from pathlib   import Path
from ROOT      import RDataFrame
from rx_common import Project
from pydantic  import BaseModel, RootModel, model_validator

_TREE     : Final[str] = 'main'
_TREE_NAME: Final[str] = 'DecayTree'

log=LogStore.add_logger('rx_data:sample_splitter')
# ------------------------------------
class FilePart(BaseModel):
    '''
    Class representing part of ROOT file

    Attributes
    ----------------
    path : Path to ROOT file
    range: Range of indices of entries in file, starting at zero, inclusive range 
    index: Index of part within file, i.e. if file has not been split, it will be zero
    split: True if this is just one part of a bigger file
    '''
    path : Path
    vers : str
    range: tuple[int,int]
    index: int
    split: bool
    # --------------------
    def friend_part_path(self, friend : str, version : str) -> Path:
        '''
        Parameters
        ----------------
        friend : Name of friend tree
        version: Version of friend tree

        Returns
        ----------------
        Path to friend tree file associated to this file part
        '''
        val  = self.friend_path(friend = friend, version = version)
        path = str(val)

        if not self.split:
            return Path(path)

        path = path.replace('.root', f'_{self.index:05}_pre_merge.root')

        return Path(path)
    # --------------------
    def friend_path(self, friend : str, version : str) -> Path:
        '''
        Parameters
        ----------------
        friend : Name of friend tree
        version: Version of friend tree

        Returns
        ----------------
        Path to friend tree file associated to this file part
        '''
        path = str(self.path)
        path = path.replace(f'/{_TREE}/'    , f'/{friend}/')
        path = path.replace(f'/{self.vers}/', f'/{version}/')

        if not self.split:
            return Path(path)

        return Path(path)
    # --------------------
    @property
    def size(self) -> int:
        '''
        Number of entries in file
        '''
        lo, hi = self.range

        return hi - lo + 1
# ------------------------------------
class FileBatch(RootModel[list[FilePart]]):
    '''
    Class representing a collection of file parts
    '''
    # ------------------------------------
    @property
    def size(self) -> int:
        '''
        Total number of entries in file batch
        '''
        sizes = [ elm.size for elm in self.root ]

        return sum(sizes)
    # ------------------------------------
    @classmethod
    def batch_parts(
        cls, 
        parts   : list[FilePart],
        entries : int) -> 'FileBatches': 
        '''
        Parameters
        --------------
        parts  : List of files or parts of files
        entries: Number of entries beyond which batch cannot go

        Returns
        ---------------
        File batches, all of them with roughly `entries` entries
        '''
        parts = sorted(parts, key = lambda x : x.size)
        batches    = FileBatches([]) 
        this_batch = FileBatch([])
        for part in parts:
            this_batch.root.append(part)

            if this_batch.size >= entries:
                batches.root.append(this_batch)
                log.debug(f'Closing batch with {this_batch.size} >= {entries}')
                this_batch = FileBatch([])

        if this_batch.root:
            batches.root.append(this_batch)

        return batches 
    # ------------------------------------
    def __str__(self) -> str:
        nfiles = len(self.root)
        name   = self.root[0].path.name if nfiles == 1 else 'multiple'
        msg    = f'{nfiles:<20}{self.size:<20}{name}'

        return msg
# ------------------------------------
class FileBatches(RootModel[list[FileBatch]]):
    '''
    Class representing a collection of file batches 
    '''
    # -------------------------
    def at(self, index : int) -> FileBatch:
        '''
        Parameters
        ---------------
        index: Index of location of batch

        Returns
        ---------------
        Batch at that index
        '''
        if index < 0:
            raise ValueError(f'Invalid index: {index}')

        if index + 1 > len(self.root):
            raise ValueError(f'Index beyond container length: {index} - {len(self.root)}')

        return self.root[index]
    # -------------------------
    @property
    def parts(self) -> list[FilePart]:
        '''
        List of file parts in all batches
        '''
        parts : list[FilePart] = []
        for batch in self.root:
            parts += batch.root

        return parts
    # -------------------------
    @property
    def size(self) -> int:
        '''
        Number of batches
        '''
        return len(self.root)
    # -------------------------
    @property
    def nentries(self) -> int:
        '''
        Number of events in all batches
        '''
        sizes = [ batch.size for batch in self.root ]

        return sum(sizes)
    # -------------------------
    def __str__(self) -> str:
        msg = 80 * '-' + '\n'
        msg+= f'{"Files":<20}{"Entries":<20}{"File names"}\n'
        msg+= 80 * '-' + '\n'
        for batch in self.root:
            msg += f'{batch}\n'
        msg += 80 * '-' + '\n'
        msg += f'Total: {len(self.root)}\n'
        msg += 80 * '-' + '\n'

        return msg
# ------------------------------------
class File(BaseModel):
    '''
    Object representing ROOT file
    '''
    vers    : str
    path    : Path
    entries : int
    # ------------------------------------
    @model_validator(mode = 'before')
    @classmethod
    def _validate(cls, data : dict[str, Any]) -> dict[str,Any]:
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
        index      = 0
        for start in range(0, self.entries, entries):
            end      = min(start + entries - 1, self.entries - 1)

            element  = FilePart(
                path = self.path,
                vers = self.vers,
                index= index,
                split= self.entries > entries, 
                range= (start, end))

            file_parts.append(element)

            index += 1

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
    @property
    def size(self) -> int:
        '''
        Number of entries in all samples
        '''
        sizes = [ file.entries for file in self.root ]

        return sum(sizes)
    # ------------------------------------
    def split(self, entries : int) -> FileBatches:
        '''
        Parameters
        -------------
        entries: Maximum number of entries allowed in part

        Returns
        -------------
        Container of file batches
        '''
        parts : list[FilePart] = []
        for file in self.root:
            parts += file.parts(entries = entries)

        return FileBatch.batch_parts(parts = parts, entries = entries)
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
        version: Version of files associated to main tree
        '''
        self._project = project
        self._version = version
        self._out_path= Path(f'.samples_{project}_{version}.json')
    # ------------------------------------
    def _get_files(self) -> Files:
        '''
        Returns
        ---------------
        List of object representing ROOT files
        '''
        ana_dir  = Path(os.environ['ANADIR'])
        dir_path = ana_dir / 'Data' / self._project / _TREE / self._version
        paths    = list(dir_path.glob(pattern = '*.root'))
        if not paths:
            raise ValueError(f'No ROOT file found in {dir_path}')

        files = [ 
            File(
                path    = path, 
                vers    = self._version,
                entries = 0) for path in paths ]

        return Files(files)
    # ------------------------------------
    def run(self, out_path : Path | None = None) -> Files:
        '''
        Parameters
        -----------------
        out_path: Path to database with samples information
                  If passed JSON path will load it, if not
                  will calculate it, cache it and return files object

        Returns
        -----------------
        Container with object representing ntuples 
        '''
        if out_path is not None and not out_path.exists():
            raise ValueError(f'Missing {out_path}')

        if not out_path:
            out_path = self._out_path 

        if out_path.exists():
            log.info(f'Found cached: {out_path}')
            return Files.from_json(path = out_path)

        log.info(f'Not found cached, caching: {out_path}')
        files  = self._get_files()
        string = files.model_dump_json(indent = 2)

        out_path.parent.mkdir(exist_ok = True, parents = True)
        out_path.write_text(string)

        return files
# ------------------------------------
