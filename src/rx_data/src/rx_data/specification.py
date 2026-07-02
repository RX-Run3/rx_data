'''
Module holding Specification and Sample classes
'''
from ROOT      import RDataFrame # type: ignore
from pathlib   import Path
from typing    import Final, Literal, overload
from pydantic  import BaseModel, ConfigDict, model_serializer
from pydantic  import RootModel, model_validator
from rx_common import Block
from dmu       import LogStore

_BLOCK         : Final[str] = 'block' # name of branch with block number
_MAIN_TREE     : Final[str] = 'main'  # name of main trees
_SYMLINK_DIR   : Final[Path]= Path('/tmp/rdf_getter/patching') # Links to patching files will be here

log = LogStore.add_logger('rx_data:specification')
# ------------------------------------
class PatchRanges(RootModel[dict[str,int]]):
    '''
    Class representing association between a file and the values a quantity that needs to be patched
    '''
    root : dict[str,int] 
    # ------------------------
    def __str__(self):
        msg = '\n'
        msg+= 20 * '-' + '\n'
        msg+= 'File patching associations\n'
        for name, value in self.root.items():
            msg += f'{"":<10}{value:<10}{name}\n'
        msg+= 20 * '-'

        return msg
# --------------------------
class File(BaseModel):
    '''
    Class meant to hold attributes of interest for ROOT files
    '''
    entries : int
    blocks  : set[Block]
    path    : Path
    # ----------------------
    def __lt__(self, other) -> bool:
        return self.path < other.path
    # ----------------------
    @classmethod
    def from_path(
        cls, 
        path : Path, 
        tree : str,
        block: Block | None = None) -> 'File':
        '''
        Parameters
        -----------------
        path : Path to ROOT file
        tree : Tree associated to the eventual dataframe 
        block: If passed, will override block in actual file. Used when patching

        Returns
        -----------------
        Instance of File class
        '''
        path_str = str(path)
        rdf      = RDataFrame(tree, path_str)
        entries  = rdf.Count().GetValue()
        if block:
            return cls(
                path    = path,
                entries = entries,
                blocks  = {block})

        arr_blk  = rdf.AsNumpy([_BLOCK])[_BLOCK]
        values   = arr_blk.tolist()
        blocks   = { Block(value = value) for value in values }

        return cls(
            path    = path,
            entries = entries, 
            blocks  = blocks)
    # ----------------------
    @model_serializer
    def serialize_model(self) -> str:
        '''
        Needed due to way RDataFrame.FromSpec reads
        JSON files to make dataframes
        '''
        return str(self.path)
# --------------------------
class Sample(BaseModel):
    '''
    Class meant to represent a sample
    '''
    model_config  = ConfigDict(frozen = True)

    files    : list[File]
    trees    : list[str]
    metadata : dict[str,str]
    # --------------------
    @model_validator(mode = 'after')
    def _validate(self) -> 'Sample':
        if len(self.trees) != 1:
            raise ValueError(f'Sample is meant to contain one tree, found: {self.trees}')

        sorted_files = sorted(self.files)
        for index, file in enumerate(sorted_files):
            self.files[index] = file

        return self
    # --------------------
    @property
    def size(self) -> int:
        '''
        Number of entries in this sample
        '''
        if len(self.trees) != 1:
            raise ValueError(f'Not one and only one tree name found: {self.trees}')

        tree_name = self.trees[0]

        paths = [ str(file.path) for file in self.files ]
        rdf   = RDataFrame(tree_name, paths)

        return rdf.Count().GetValue()
    # --------------------
    def get_file_paths(self, block : Block) -> list[Path]:
        '''
        Parameters
        ----------------
        block: I.e. part of dataset

        Returns
        ----------------
        Files containing data from that block
        '''
        return [ file.path for file in self.files if block in file.blocks ]
    # --------------------
    @property
    def ranges(self) -> PatchRanges:
        '''
        Returns
        ---------------
        Object storing ranges and blocks needed for patching
        '''
        last = 0
        data : list[tuple[int,int,int]] = []
        for file in self.files:
            blocks = list(file.blocks)
            if len(blocks) > 1:
                block = _INVALID_BLOCK
            else:
                block = blocks[0].to_int()

            entry = last, last + file.entries, block 
            data.append(entry)
            last += file.entries

        return PatchRanges(root = data)
    # --------------------
    def patch(self, paths : list[Path], block : Block) -> 'Sample':
        '''
        Parameters
        -----------------
        paths: List of paths meant to extend sample
        block: Block number associated
        '''
        tree        = self.trees[0]
        paths       = sorted(paths)

        extra_files = [ File.from_path(path, tree, block) for path in paths ]

        return self.model_copy(update = {'files' : self.files + extra_files})
# --------------------------
class Specification(BaseModel):
    '''
    Class meant to represent a specification needed
    to build ROOT dataframes
    '''
    model_config = ConfigDict(frozen=True)

    friends : dict[str,Sample]
    samples : dict[str,Sample]
    # --------------------------
    @property
    def ranges(self) -> PatchRanges:
        main_sample = self.samples[_MAIN_TREE]

        return main_sample.ranges
    # --------------------------
    def print_ranges(self) -> None:
        log.debug(20 * '-')
        log.debug('Patching ranges:')
        for ientry, fentry, iblock in self.ranges.root:
            log.debug(f'{"":<10}{ientry:<10}{fentry:<10}{iblock:<10}')
        log.debug(20 * '-')
# --------------------------
