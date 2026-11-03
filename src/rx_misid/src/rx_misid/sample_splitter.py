'''
Module holding SampleSplitter class
'''

import numpy
import pandas as pnd

from typing          import Final
from pathlib         import Path
from ROOT            import RDF
from dmu             import LogStore
from dmu.rdataframe  import utilities as rut
from dmu.workflow    import Cache     as Wcache

from .types          import MisIDSampleSplitting

log=LogStore.add_logger('rx_misid:sample_splitter')

PION_ID : Final[int] = 211
KAON_ID : Final[int] = 321
# --------------------------------
class SampleSplitter(Wcache):
    '''
    What this returns
    -----------------------
    Class meant to split a dataframe with simulated
    data it will tag events using the `kind` column as kaon or pion events.

    It adds columns:

    - hadron: pion or kaon, depending on hadron tagging cut from config,
              if candidate is tagged as pion (kaon) then both tracks will be pions (kaons)
    '''
    # --------------------------------
    def __init__(
        self,
        rdf     : RDF.RNode,
        out_dir : Path,
        cfg     : MisIDSampleSplitting):
        '''
        Parameters
        --------------------
        rdf     : Input dataframe with data to split, It should have attached a `uid` attribute, the unique identifier
        out_dir : Path (WRT ANADIR) to directory with outputs
        cfg     : omegaconf dictionary with configuration specifying how to split the samples
        '''
        nentries = rdf.Count().GetValue()
        if nentries == 0:
            raise ValueError('Got an empty dataframe')

        super().__init__(
            out_path = out_dir,
            args     = [rdf.uid, cfg.model_dump()])

        self._cfg = cfg
        self._rdf = rdf
    # --------------------------------
    def _id_from_array(self, array : numpy.ndarray) -> int:
        '''
        Parameters
        -------------
        array: Numpy array with particle IDs

        Returns
        -------------
        Absolute value of particle ID. If multiple IDs are found, raise.
        '''
        array = numpy.abs(array)
        if not numpy.all(array == array[0]):
            rep    = self._rdf.Report()
            rep.Print()
            unique = numpy.unique(array)
            log.error(unique)
            raise ValueError('Array of IDs contains multiple values')

        particle_id = array[0]

        return particle_id
    # ----------------------
    def _particle_from_simulation(self) -> str:
        '''
        Returns
        -------------
        Name of particle associated to MC L1 and L2 leptons, pion or kaon.
        If neither, raise
        '''
        l_col = [ name.c_str() for name in self._rdf.GetColumnNames() ]

        if 'L1_TRUEID' not in l_col or 'L2_TRUEID' not in l_col:
            raise ValueError('No simulation hadron ID found, sample is data')

        d_trueid = self._rdf.AsNumpy(['L1_TRUEID', 'L2_TRUEID'])
        arr_l1id = d_trueid['L1_TRUEID']
        arr_l2id = d_trueid['L2_TRUEID']

        lep1_id  = self._id_from_array(array=arr_l1id)
        lep2_id  = self._id_from_array(array=arr_l2id)

        if lep1_id != lep2_id:
            raise ValueError(f'Lepton IDs differ: {lep1_id} != {lep2_id}')

        if   lep1_id == PION_ID:
            particle = 'pion'
        elif lep1_id == KAON_ID:
            particle = 'kaon'
        else:
            raise ValueError(f'Unexpected lepton ID: {lep1_id}')

        log.debug(f'Found hadron: {particle}')

        return particle
    # --------------------------------
    def get_sample(self) -> pnd.DataFrame:
        '''
        Returns pandas dataframe with data from input ROOT dataframe
        the output contains the `hadron` column, signaling if this is
        a kaon (kkk) or pion sample (kpipi)
        '''
        parquet_path = self._out_path / 'sample.parquet'
        if self._copy_from_cache():
            log.warning(f'Cached path found, reusing: {parquet_path}')
            df = pnd.read_parquet(parquet_path, engine='pyarrow')

            return df

        particle     = self._particle_from_simulation()
        columns      = self._cfg.branches
        df           = rut.rdf_to_df(rdf=self._rdf, columns=columns)
        df['hadron'] = particle
        df['block']  = df['block'].astype(int)

        df.to_parquet(parquet_path, engine='pyarrow')
        self._cache()
        return df
# --------------------------------
