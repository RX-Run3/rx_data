'''
Module holding RDFLoader class
'''
import time
import cppyy

from contextlib       import contextmanager
from dask.distributed import Client
from pathlib          import Path
from ROOT             import RDF
from dmu              import LogStore

log=LogStore.add_logger('rx_data:rdf_loader')
# ----------------------------------
class RDFLoader:
    '''
    Class meant to hold functionality to provide ROOT dataframes.
    It is supposed to handle:

    - Network delays
    - Timeouts
    '''
    _CLIENT : Client | None = None
    # ----------------------
    @classmethod
    def client(cls, client : Client):
        '''
        Parameters
        -------------
        client: Dask client to use to process dataframe

        Returns
        -------------
        Context manager
        '''
        old_val = cls._CLIENT

        log.info('Using user provided dask client')

        @contextmanager
        def _context():
            try:
                cls._CLIENT = client
                yield
            finally:
                cls._CLIENT = old_val 

        return _context()
    # ----------------------
    @classmethod
    def from_conf(
        cls,
        ntries : int,
        wait   : int,
        path   : Path) -> RDF.RNode:
        '''
        Parameters
        -------------
        ntries: Number of times to retry loading of data before raising exception
        wait  : Number of seconds to wait between failed tries
        path: Path to JSON file holding configuration needed to build dataframe

        Returns
        -------------
        ROOT dataframe
        '''
        itry = 0

        while itry < ntries:
            try:
                if cls._CLIENT is None:
                    log.debug(f'Not using any client to load: {path}')
                    rdf = RDF.Experimental.FromSpec(str(path))
                else:
                    log.debug(f'Using user provided client to load: {path}')
                    rdf = RDF.Experimental.FromSpec(str(path), executor = cls._CLIENT)

                nentries = rdf.Count().GetValue()
                log.debug(f'Succeeding loading {nentries} entries from: {path}')

                return rdf
            except (cppyy.gbl.std.runtime_error, RuntimeError):
                log.warning(f'Loading of dataframe failed, retrying in {wait} seconds')
                time.sleep(wait)
                itry += 1

        raise RuntimeError(f'Failed to load {path}')
# ----------------------------------
