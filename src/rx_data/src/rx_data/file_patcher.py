'''
Module holding FilePatcher class
'''
import re
import tempfile

from pathlib     import Path
from typing      import Final
from ROOT        import RDataFrame, RDF # type: ignore
from dmu         import LogStore
from dmu.generic import utilities as gut

log=LogStore.add_logger('rx_data:file_patcher')

_HASH_REGEX : Final[str] = r'.*_(\w{10})\.root$'
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
        self._blocks : dict[str,int] = gut.load_data(
            package = 'rx_data_data', 
            fpath   = 'rdf_getter/blocks.json')
    # -----------------------------
    @property
    def hashes(self) -> set[str]:
        '''
        List of strings representing hashes in ROOT files
        hashes identify job that created this file
        '''
        return set(self._blocks) 
    # -----------------------------
    def _add_block(
        self, 
        block : int | None, 
        path  : Path) -> int:
        '''
        Parameters
        ------------
        block : Block to add
        path  : Path to ROOT file

        Returns
        ------------
        Statust code:

        -2: Block was not added, because MCDecayTree was not found 
        -1: Block was not added, because block was not found 
        0 : Block was not added, because it was already there
        1 : Block was added
        2 : Dry run
        '''
        try:
            rdf_input = RDataFrame('MCDecayTree', str(path))
            entries   = rdf_input.Count().GetValue()

            log.debug(f'Found MCDecayTree with {entries} entries')
        except Exception:
            log.debug(f'MCDecayTree not found in {path}')
            return -2

        columns = [ column.c_str() for column in rdf_input.GetColumnNames() ]
        if 'block' in columns:
            log.debug(f'Column already present in: {path}')
            return 0

        if block is None:
            log.warning(f'Block not found for {path}')
            return -1

        log.debug(f'Defining block == {block} for {path}')
        if self._dry_run:
            log.debug('Dry run, not adding any column')
            return 2

        with tempfile.NamedTemporaryFile(suffix='.root', delete=False, dir='/tmp') as value:
            tmp_path = str(value.name)
            log.debug(f'Storing temporary MCDecayTree in: {tmp_path}')
            rdf_input.Snapshot('MCDecayTree', tmp_path)
            rdf  = RDataFrame('MCDecayTree', tmp_path)

            rdf  = rdf.Define('block', str(block))
            opts = RDF.RSnapshotOptions()
            opts.fMode              = 'update'
            opts.fOverwriteIfExists = True

            rdf.Snapshot(
                options  = opts,
                treename = 'MCDecayTree', 
                filename = str(path), 
            )

        return 1
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
        2 : Dry run
        '''
        if self._dry_run:
            self._counter += 1
            log.info(f'{self._counter:<20}{path}')

        if not path.name.startswith('mc_'):
            log.debug(f'Skipping non MC file: {path}')
            return -3

        if not path.exists():
            raise ValueError(f'File not found: {path}')

        mtch = re.match(_HASH_REGEX, str(path))
        if not mtch:
            raise ValueError(f'Cannot extract hash from: {path}')

        hash_val = mtch.group(1)
        block    = self._blocks.get(hash_val)

        return self._add_block(block = block, path = path)
# -----------------------------
