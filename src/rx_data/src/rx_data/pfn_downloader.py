'''
Module with PFNDownloader class
'''

import os
import time
import tqdm
import math

from pydantic           import BaseModel
from XRootD             import client   as clt
from concurrent.futures import ThreadPoolExecutor
from functools          import cached_property
from typing             import Final, Protocol
from pathlib            import Path
from dmu                import LogStore

log=LogStore.add_logger('rx_data:pfn_downloader')

_PFN_PREFIX : Final[str] = 'root://x509up_u1000@eoslhcb.cern.ch//eos/lhcb/grid/user'
# ---------------------------------
class PFNHolder(Protocol):
    '''
    Class meant to represent object that can provide PFNs
    '''
    @cached_property
    def pfns(self) -> set[str]:
        ...
# ---------------------------------
class PFNDownloaderConf(BaseModel):
    '''
    Class meant to configure PFNDownloader
    '''
    chunks      : int
    chunksize   : int
    version     : str
    out_dir     : Path
    dry_run     : bool
    nthread     : int
    failed_pfns : list[str] = []
# ---------------------------------
class PFNDownloader:
    '''
    Class meant to download PFNs
    '''
    # --------------------------------------------
    def __init__(
        self,
        cfg     : PFNDownloaderConf,
        samples : PFNHolder):
        '''
        Parameters
        ---------------
        samples: Object representing samples in the AnalysisProductions
        '''
        self._samples = samples
        self._cfg     = cfg
    # --------------------------------------------------
    def _split_pfns(self, pfns : set[str]) -> list[list[str]]:
        '''
        Parameters
        ------------------
        pfns: List of PFNs

        Returns
        ------------------
        List of lists of PFNs, split evenly
        '''
        npfn        = len(pfns)
        thread_size = math.floor(npfn / self._cfg.nthread)
        l_pfns      = list(pfns)
        groups      = [ l_pfns[i_pfn : i_pfn + thread_size] for i_pfn in range(0, npfn, thread_size) ]

        log.debug(30 * '-')
        log.debug(f'{"Thread":<10}{"PFNs":<20}')
        log.debug(30 * '-')
        for i_thread, group in enumerate(groups):
            npfn = len(group)
            log.debug(f'{i_thread:<10}{npfn:<20}')

        return groups
    # --------------------------------------------
    def _delete_superfluous_files(self, fnames : set[str]) -> None:
        '''
        Parameters
        ------------------
        fnames: Set of file names
        '''
        if not fnames:
            log.debug('No superfluous files found')
            return

        log.info(f'Found {len(fnames)} superfluous files in: {self._cfg.out_dir/self._cfg.version}')
        for name in sorted(fnames):
            log.info(name)

        dec = input('Delete superfluous files? [y/n]')
        if dec not in ['y', 'n']:
            raise ValueError('Choose between [y,n]')

        if dec == 'n':
            log.debug('Not deleting superfluous files')
            return

        log.info('Deleting files:')
        for fname in tqdm.tqdm(fnames, ascii=' -'):
            path = self._cfg.out_dir / self._cfg.version / fname
            log.debug(path)
            if not self._cfg.dry_run:
                path.unlink()
    # --------------------------------------------
    def _get_pfns_to_download(
        self,
        fnames : set[str],
        pfns   : set[str]) -> set[str]:
        '''
        Parameters
        ----------------
        fnames: Set of filenames (not paths) already downloaded
        pfns  : Set of PFNs to download

        Returns
        ----------------
        Set of PFNs that have not been downloaded
        '''
        nold = len(pfns)

        pfns_to_download = set()
        for pfn in pfns:
            name_to_download = os.path.basename(pfn)
            if name_to_download in fnames:
                continue

            pfns_to_download.add(pfn)

        nnew = len(pfns_to_download)

        log.warning(f'Will download {nnew} out of {nold} requested PFNs')

        return pfns_to_download
    # --------------------------------------------
    def _cleanup_pfns(self, pfns : set[str]) -> set[str]:
        '''
        Parameters
        ---------------
        pfns: List of PFNs

        Returns
        ---------------
        Subset of input list
        '''
        s_name_to_download  = { os.path.basename(pfn) for pfn in pfns }
        dir_downloaded      = self._cfg.out_dir / self._cfg.version
        paths_downloaded    = list(dir_downloaded.rglob(pattern = '*.root'))

        if not paths_downloaded:
            log.info(f'No downloaded files found in {dir_downloaded}, check for superfluous paths skipped')
            return pfns

        s_name_downloaded  = {os.path.basename(path) for path in paths_downloaded}
        s_name_superfluous = s_name_downloaded - s_name_to_download

        self._delete_superfluous_files(fnames = s_name_superfluous)
        pfns       = self._get_pfns_to_download(
            fnames = s_name_downloaded,
            pfns   = pfns)

        return pfns
    # --------------------------------------------------
    @staticmethod
    def download_group(
        cfg  : PFNDownloaderConf,
        pfns : list[str],
        pbar : tqdm.std.tqdm) -> None:
        '''
        Parameters
        -----------------
        pfns: List of PFNs
        pbar: Progressbar object
        '''
        for pfn in pfns:
            try:
                PFNDownloader.download_pfn(pfn = pfn, cfg = cfg)
            except Exception as exc:
                log.debug(f'Failed to download: {pfn}')
                log.debug(f'Reason: {exc}', exc_info = True)
                lfn = pfn.removeprefix(_PFN_PREFIX)
                cfg.failed_pfns.append(lfn)

            pbar.update(1)
    # --------------------------------------------------
    @staticmethod
    def download_pfn(
        cfg : PFNDownloaderConf,
        pfn : str) -> None:
        '''
        Parameters
        --------------
        cfg : Config object
        pfn : PFN
        '''
        file_name = os.path.basename(pfn)
        out_path  = cfg.out_dir / cfg.version / file_name
        if os.path.isfile(out_path):
            log.debug(f'Skipping downloaded file: {pfn}')
            return

        if cfg.dry_run:
            return

        log.debug(f'Downloading: {pfn}')

        process = clt.CopyProcess()
        process.add_job(
            pfn,
            str(out_path),
            parallelchunks= cfg.chunks,
            chunksize     = cfg.chunksize,
        )
        process.prepare()
        status, _ = process.run()

        if status.ok: # type: ignore
            log.debug('Downloaded successfully')
        else:
            raise ValueError(f'Failed to download: {status.message}') # type: ignore
    # ------------------------------------
    def _download_groups_with_threads(self, groups : list[list[str]]):
        '''
        Parameters
        ------------------
        groups: List of groups of PFNs
        '''
        with ThreadPoolExecutor(max_workers=self._cfg.nthread) as executor:
            l_future = []
            for group in groups:
                pbar = tqdm.tqdm(total=len(group))
                future = executor.submit(self.download_group, self._cfg, group, pbar)
                l_future.append(future)

            for future in l_future:
                if future.exception():
                    print(future.exception())

        time.sleep(1)
    # ------------------------------------
    def _download_groups(
        self,
        groups : list[list[str]]) -> None:
        '''
        Parameters
        ------------------
        groups: List of groups of PFNs
        '''
        if self._cfg.nthread > 1:
            log.info(f'Using {self._cfg.nthread} threads')
            self._download_groups_with_threads(groups = groups)
        else:
            log.info('Using single thread')
            pfns = [ pfn for pfns in groups for pfn in pfns ]
            pbar = tqdm.tqdm(total=len(pfns))
            self.download_group(pfns = pfns, cfg = self._cfg, pbar = pbar)

        if not self._cfg.failed_pfns:
            return

        failed_pfns = sorted(self._cfg.failed_pfns)

        log.error(20 * '-')
        log.error(f'Failed to download {len(failed_pfns)} files:')
        log.error(20 * '-')
        for pfn in failed_pfns:
            log.info(pfn)
    # ------------------------------------
    def run(self) -> None:
        '''
        Starts download
        '''
        if not self._samples.pfns:
            raise ValueError('No PFNs found')

        pfns = self._cleanup_pfns(pfns = self._samples.pfns)
        if not pfns:
            log.info('No PFNs need to be downloaded')
            return

        groups = self._split_pfns(pfns = pfns)
        self._download_groups(groups = groups)
# ---------------------------------
