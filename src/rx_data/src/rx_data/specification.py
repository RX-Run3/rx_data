'''
Module holding Specification and Sample classes
'''
from ROOT        import RDataFrame, RDF
from pathlib     import Path
from typing      import Final, Literal, overload
from pydantic    import BaseModel, ConfigDict, Field, model_serializer
from pydantic    import RootModel, model_validator
from rx_common   import Block
from dmu         import LogStore
from dmu.fsystem import get_tmp_path

_BLOCK     : Final[str] = 'block' # name of branch with block number
_MAIN_TREE : Final[str] = 'main'  # name of main trees

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
    @overload
    @classmethod
    def from_path(
        cls,
        path : Path,
        tree : str,
        ftree: str,
        patch: Literal[True],
        block: Block,
    ) -> 'File': ...
    @overload
    @classmethod
    def from_path(
        cls,
        path : Path,
        tree : str,
        ftree: str,
        patch: Literal[False],
        block: Block | None,
    ) -> 'File': ...
    @classmethod
    def from_path(
        cls,
        path : Path,
        tree : str,
        ftree: str,
        patch: bool,
        block: Block | None) -> 'File':
        '''
        Parameters
        -----------------
        path : Path to ROOT file
        tree : Tree associated to the eventual dataframe
        patch: If true, will patch with block and with this file
        ftree: Friend tree name, e.g. mva
        block: If passed, will
               - Override block in actual file.
               - Symlink original file using new-block based naming
               Used when patching

        Returns
        -----------------
        Instance of File class
        '''
        path_str = str(path)
        rdf      = RDataFrame(tree, path_str)
        entries  = rdf.Count().GetValue()
        if entries == 0:
            log.warning(f'Found empty file: {path}/{tree}')
            return cls(
                path    = path,
                entries = entries,
                blocks  = set())

        # Here we do not patch
        if   block is None:
            # Main tree that needs patching
            blocks = cls._blocks_from_rdf(rdf = rdf, path = path, tree = tree)
        elif patch:
            fname  = path.name.replace('.root', '_')
            link   = get_tmp_path(
                directory = f'rx_data/specification/{ftree}',
                prefix    = fname,
                extension = 'root')

            link.symlink_to(target = path)
            path   = link
            blocks = {block}
        else:
            blocks = {block}

        return cls(
            path    = path,
            entries = entries,
            blocks  = blocks)
    # ----------------------
    @classmethod
    def _blocks_from_rdf(
        cls,
        rdf : RDF.RNode,
        path: Path,
        tree: str) -> set[Block]:
        '''
        Returns set of blocks in a given ROOT dataframe
        '''
        columns = [ name.c_str() for name in rdf.GetColumnNames() ]

        if _BLOCK not in columns:
            raise ValueError(f'Column {_BLOCK} not found for : {path}:{tree}')

        arr_blk  = rdf.AsNumpy([_BLOCK])[_BLOCK]
        svalues  = arr_blk.tolist()
        ivalues  = [ int(value) for value in svalues ]
        blocks   = { Block(value = value) for value in ivalues }

        return blocks
    # ----------------------
    @property
    def is_empty(self) -> bool:
        '''
        True if no entries found in file
        '''
        return self.entries == 0
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
    ranges   : PatchRanges = Field(default = PatchRanges(root = {}), exclude = True)
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
        block: Block representing part of data

        Returns
        ----------------
        Files containing data from that block
        '''
        files = [ file.path for file in self.files if block in file.blocks ]

        if not files:
            for file in self.files:
                log.error(file.blocks)

            raise ValueError(f'No files found from block {block}')

        return files
    # --------------------
    def _update_ranges(self, files : list[File], block : Block) -> None:
        '''
        Parameters
        -------------
        paths: Patching files, i.e. the ones contained symlinks to patching ROOT files
        block: Block been patched
        '''
        tree = self.trees[0]
        for file in files:
            key = f'{file.path}/{tree}'
            self.ranges.root[key] = block.to_int()
    # --------------------
    def patch(self, paths : list[Path], block : Block) -> 'Sample':
        '''
        Parameters
        -----------------
        paths: List of paths meant to extend sample
        block: Block number associated
        '''
        if not paths:
            raise ValueError('No patching paths found')

        tree         = self.trees[0]
        ftree        = self.metadata['kind']
        paths        = sorted(paths)
        linked_files = [
            File.from_path(
                path = path,
                tree = tree,
                patch= True,
                block= block,
                ftree= ftree) for path in paths ]

        non_empty_files : list[File] = [ file for file in linked_files if not file.is_empty ]
        if not non_empty_files:
            for file in linked_files:
                log.error(file.path)
            raise ValueError('All patching files are empty')

        self._update_ranges(files = non_empty_files, block = block)

        return self.model_copy(update = {'files' : self.files + non_empty_files})
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
