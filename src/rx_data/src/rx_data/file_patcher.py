'''
Module holding FilePatcher class
'''
import array

from pathlib     import Path
from typing      import Final
from ROOT        import RDataFrame, TFile
from dmu         import LogStore

log=LogStore.add_logger('rx_data:file_patcher')

_BLOCKNAME : Final[str] = 'block'
# -----------------------------
class FilePatcher:
    '''
    Class meant to:

    - Add block number to MCDecayTree whenever missing
    '''
    # -----------------------------
    def __init__(self, dry_run : bool):
        '''
        Parameters
        ------------
        dry_run: If true will stop before adding column
        '''
        self._counter = 0
        self._dry_run = dry_run
    # -----------------------------
    def __get_block(self, path : Path) -> int:
        '''
        Parameters
        ----------------
        path: Path to ROOT file

        Returns
        ----------------
        Block number in DecayTree
        '''
        if self.__is_missing_block(path = path, tree = 'DecayTree'):
            raise ValueError(f'DecayTree is missing column: {_BLOCKNAME}')

        rdf       = RDataFrame('DecayTree', str(path))
        arr_block = rdf.AsNumpy([_BLOCKNAME])[_BLOCKNAME]
        blocks    = arr_block.tolist()

        if len(set(blocks)) != 1:
            raise ValueError(f'Expected one block found: {set(blocks)}')

        return blocks[0]
    # -----------------------------
    def __add_block(
        self,
        block : int,
        path  : Path) -> int:
        '''
        Parameters
        ------------
        block : Block to add
        path  : Path to ROOT file

        Returns
        ------------
        Statust code:

        0 : Block was not added, because it was already there
        1 : Block was added
        2 : Dry run, but would have added a missing block
        '''
        rdf_input = RDataFrame('MCDecayTree', str(path))
        columns   = [ column.c_str() for column in rdf_input.GetColumnNames() ]
        if 'block' in columns:
            log.debug(f'Column already present in: {path}')
            return 0

        log.debug(f'Defining block == {block} for {path}')
        if self._dry_run:
            log.debug('Dry run, not adding any column')
            return 2

        file = TFile(str(path), "UPDATE")
        tree = file.Get('MCDecayTree')

        val = tree.GetEntry(0)
        if val <= 0:
            log.warning(f'Corrupted: {path}')

            file.Close()
            return 1

        value_arr  = array.array('i', [block])
        new_branch = tree.Branch('block', value_arr, "block/I")

        for i in range(int(tree.GetEntries(""))):
            tree.GetEntry(i)
            new_branch.Fill()

        file.Write()
        file.Close()

        return 1
    # -----------------------------
    def __is_missing_block(self, path : Path, tree : str) -> bool:
        '''
        If true, the patching is needed
        '''
        rdf     = RDataFrame(tree, str(path))
        columns = [ name.c_str() for name in rdf.GetColumnNames() ]

        if _BLOCKNAME not in columns:
            return True

        return False
    # -----------------------------
    def __is_missing_tree(self, path : Path, tree : str) -> bool:
        ifile = TFile(str(path))
        key   = ifile.Get(tree)

        return not key
    # -----------------------------
    def run(self, path : Path) -> int:
        '''
        Parameters
        -------------
        path: Path to ROOT file to patch

        Returns
        ------------
        Statust code:

        -3: Block was not added, because file is not MC
        -2: Block was not added, because MCDecayTree was not found
        -1: Block was not added, because block was not found
        0 : Block was not added, because it was already there
        1 : Block was added
        2 : Dry run, but would have added a missing block
        '''
        if self._dry_run:
            self._counter += 1
            log.debug(f'{self._counter:<20}{path}')

        if not path.name.startswith('mc_'):
            log.debug(f'Skipping non MC file: {path}')
            return -3

        if not path.exists():
            raise ValueError(f'File not found: {path}')

        if self.__is_missing_tree(path = path, tree = 'MCDecayTree'):
            return -2

        if not self.__is_missing_block(path = path, tree = 'MCDecayTree'):
            return 0

        block = self.__get_block(path = path)

        log.debug(f'Found block: {block}')

        return self.__add_block(block = block, path = path)
# -----------------------------
