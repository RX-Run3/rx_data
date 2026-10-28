'''
Module use to hold RDFGetter12 class
'''
import os

from contextlib  import contextmanager
from pathlib     import Path
from typing      import Final
from ROOT        import RDataFrame, RDF
from dmu         import LogLevels, LogStore
from dmu.generic import utilities as gut

log=LogStore.add_logger('rx_data:rdf_getter12')
_ANADIR : Final[Path] = Path(os.environ['ANADIR'])
# --------------------------
class RDFGetter12:
    '''
    This class is meant to allow access to Run1/2 ntuples
    '''
    _d_sel : dict[str,str] = {}
    # --------------------------
    def __init__(self, sample : str, trigger : str, dset : str):
        '''
        sample : Name of data/MC sample, e.g. Bu_Kee_eq_btosllball05_DPC
        trigger: Hlt2 trigger, e.g. Hlt2RD_BuToKpEE_MVA, meant to be translated as ETOS or MTOS
        dset   : Year, e.g. 2018
        '''
        self._dset   = '*' if dset == 'all' else dset
        self._ntp_dir= 'no_bdt_q2_mass'
        self._version= 'v10.21p3'

        self._l_sig_sample = ['Bu_Kee_eq_btosllball05_DPC', 'Bu_Kmumu_eq_btosllball05_DPC']
        self._l_ctr_sample = ['Bu_JpsiK_ee_eq_DPC'        , 'Bu_JpsiK_mm_eq_DPC']
        self._l_sim_sample = self._l_sig_sample + self._l_ctr_sample

        self._d_trigger    = {
            'Hlt2RD_BuToKpEE_MVA'  : 'ETOS',
            'Hlt2RD_BuToKpMuMu_MVA': 'MTOS'}

        self._sample = self._get_sample(sample)
        self._trigger= self._d_trigger[trigger]
        self._cfg    = gut.load_conf(package='rx_data_data', fpath='rdf_getter12/config.yaml')
    # --------------------------
    def _add_columns(self, rdf : RDF.RNode) -> RDF.RNode:
        '''
        Parameters
        -------------
        rdf : ROOT dataframe

        Returns
        -------------
        Dataframe with columns added
        '''
        if 'MuMu' in self._trigger:
            d_def = self._cfg.definitions['MM']
        else:
            d_def = self._cfg.definitions['EE']

        if self._sample in self._l_sim_sample:
            d_def_mc = self._cfg.definitions['MC']
            d_def.update(d_def_mc)

        if len(d_def) == 0:
            raise ValueError('No column definitions found')

        for name, expr in d_def.items():
            log.debug(f'{name:<30}{expr}')
            rdf = rdf.Define(name, expr)

        return rdf
    # --------------------------
    def _get_sample(self, sample : str) -> str:
        '''
        Parameters
        --------------
        sample: Run 3 sample name, e.g. Bu_Kee_eq_btosllball05_DPC

        Returns
        --------------
        Run1/2 sample name, e.g. sign
        '''
        if sample in self._l_sig_sample:
            return 'sign'

        if sample in self._l_ctr_sample:
            return 'ctrl'

        raise NotImplementedError(f'Invalid sample: {sample}')
    # --------------------------
    def _apply_selection(self, rdf : RDF.RNode) -> RDF.RNode:
        '''
        Parameters
        -------------
        rdf : ROOT dataframe before selection

        Returns
        -------------
        Dataframe after selection
        '''
        if len(RDFGetter12._d_sel) == 0:
            return rdf

        log.info('Applying custom selection')
        for name, expr in RDFGetter12._d_sel.items():
            log.debug(f'{name:<30}{expr}')
            rdf = rdf.Filter(expr, name)

        if log.getEffectiveLevel() < LogLevels.info:
            rep = rdf.Report()
            rep.Print()

        return rdf
    # --------------------------
    def get_rdf(self) -> RDF.RNode:
        '''
        Returns ROOT dataframe with dataset
        '''
        ntp_dir  = _ANADIR / f'Data/run12/{self._sample}/{self._version}'

        log.info(f'Picking paths from {ntp_dir}')

        l_path = [ str(path) for path in ntp_dir.rglob(f'{self._dset}_{self._trigger}/*.root') ]
        npath  = len(l_path)
        if npath == 0:
            raise ValueError(f'No file found in: {ntp_dir}')

        rdf = RDataFrame(self._trigger, l_path)
        rdf = self._add_columns(rdf=rdf)
        rdf = self._apply_selection(rdf=rdf)

        return rdf
    # ----------------------
    @classmethod
    def add_selection(cls, d_sel : dict[str,str]):
        '''
        Parameters
        -------------
        d_sel : Dictionary with selection, the keys are the labels and
                the values are the expressions
        '''
        @contextmanager
        def _context():
            old_val    = cls._d_sel
            cls._d_sel = d_sel
            try:
                yield
            finally:
                cls._d_sel = old_val

        return _context()
# --------------------------
