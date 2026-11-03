'''
This module contains the NtuplePartitioner class
'''
import os
import fnmatch

from pathlib      import Path
from dmu          import LogStore
from rx_common    import Project
from dmu.generic  import version_management as vman

log=LogStore.add_logger('rx_data:ntuple_partitioner')
# -------------------------------------------
class NtuplePartitioner:
    '''
    This class will:

    - Load paths for ntuples
    - Provide a subset of paths according to user-provided partition
    '''
    # ----------------------
    def __init__(
        self,
        project  : Project,
        kind     : str):
        '''
        Parameters
        -------------
        project  : E.g. rk, rkst, rk_nopid
        kind     : Type of tree, e.g. main, mva, hop...
        '''
        self._kind      = kind
        self._proj      = project
        self._ana_dir   = Path(os.environ['ANADIR'])

        self._s_ecorr   = {'brem_track_2'}
    # ---------------------------------
    def _print_groups(
        self,
        groups     : dict[int,list[Path]],
        sizes      : dict[int,int],
        this_group : int) -> None:
        '''
        Prints list of groups with number of files and sizes

        Parameters
        -------------------
        groups    : Dictionary mapping group index with list of paths to ROOT files
        sizes     : Sizes of each group of files
        this_group: Index of current group been processed
        '''
        log.info(30 * '-')
        log.info(f'{"Group":<10}{"NFiles":<10}{"Size":<10}')
        log.info(30 * '-')
        for igroup, l_file in groups.items():
            size  = sizes[igroup]
            nfile = len(l_file)

            if igroup == this_group:
                log.info(f'{igroup:<10}{nfile:<10}{size:<10}{"<---":<10}')
            else:
                log.info(f'{igroup:<10}{nfile:<10}{size:<10}')

        log.info(30 * '-')
    # ---------------------------------
    def _get_path_size(self, path : Path) -> int:
        '''
        Parameters
        ----------------
        path : Path to ROOT file

        Returns
        ----------------
        Size in Megabytes
        '''
        size = path.stat().st_size / 1024 ** 2
        size = int(size)

        return size
    # ---------------------------------
    def _get_partition(
        self,
        l_path : list[Path],
        igroup : int,
        ngroup : int) -> list[Path]:
        '''
        Parameters
        -----------------
        l_path : List of paths to ROOT files
        index  : Index of the partition
        total  : Number of partitions

        Returns
        -----------------
        List of paths to ROOT files corresponding to
        igroup, when splitting into equally sized (in Megabytes) ngroup groups
        '''
        d_path      = { path : self._get_path_size(path) for path in l_path }
        sorted_files= sorted(d_path.items(), key=lambda x: x[1], reverse=True)

        groups      = {i: [] for i in range(ngroup)}
        group_sizes = {i: 0  for i in range(ngroup)}

        for file_path, size in sorted_files:
            min_group = min(group_sizes, key=lambda index : group_sizes[index])
            groups[min_group].append(file_path)
            group_sizes[min_group] += size

        self._print_groups(groups=groups, sizes=group_sizes, this_group = igroup)

        norg  = len(l_path)
        l_path= groups[igroup]
        npar  = len(l_path)
        log.info(f'Processing group of {npar} files out of {norg}')
        for path in l_path:
            log.debug(path)

        return l_path
    # ---------------------------------
    def _filter_paths(self, l_path : list[Path]) -> list[Path]:
        ninit = len(l_path)
        log.debug(f'Filtering {ninit} paths')
        for path in l_path:
            log.verbose(path)

        if self._kind in self._s_ecorr:
            # For electron corrections, drop muon paths
            l_path = [ path for path in l_path if 'MuMu' not in str(path) ]

        nfnal = len(l_path)
        log.debug(f'Filtered -> {nfnal} paths')

        return l_path
    # ----------------------
    def get_paths(self, index : int, total : int) -> list[Path]:
        '''
        Parameters
        -------------
        index: Index of the partition
        total: Number of partitions

        Returns
        -------------
        Set of paths making up the requested partition
        '''
        dir_path = self._ana_dir / f'Data/{self._proj}/{self._kind}'
        log.debug(f'Looking for latest version in: {dir_path}')

        data_dir = vman.get_last_version(dir_path = dir_path, version_only = False)
        log.debug(f'Lookig for files in: {data_dir}')

        l_path   = list(data_dir.glob('*.root'))
        l_path   = self._filter_paths(l_path)
        l_path   = self._get_partition(
            l_path = l_path,
            igroup = index,
            ngroup = total)

        nfiles   = len(l_path)
        if nfiles == 0:
            raise ValueError(f'No file found in: {data_dir}')

        log.info(f'Picking up {nfiles} file(s) from {data_dir}')

        return l_path
# -------------------------------------------
