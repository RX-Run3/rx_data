'''
Module containing selector class
'''

from typing                 import Union
from ROOT                   import RDataFrame

from dmu.rdataframe.atr_mgr import AtrMgr
from dmu.logging.log_store  import LogStore

import post_ap.utilities as utdc

log = LogStore.add_logger('post_ap:selector')
# -------------------------------------------------------------------
class Selector:
    '''
    Class used to apply selections to ROOT dataframes
    '''
    # -------------------------------------------------------------------
    def __init__(self, rdf : RDataFrame, is_mc : bool):
        '''
        rdf    : ROOT dataframe
        is_mc  : MC or real data?
        '''

        self._rdf       = rdf
        self._is_mc     = is_mc

        self._atr_mgr   : AtrMgr
        self._d_sel     : dict
        self._d_rdf     : dict[str,   RDataFrame] = {}

        self._initialized = False
    # -------------------------------------------------------------------
    def _initialize(self):
        if self._initialized:
            return

        if self._is_mc not in [True, False]:
            log.error(f'Invalid value for is_mc: {self._is_mc}')
            raise ValueError

        self._atr_mgr  = AtrMgr(self._rdf)
        cfg_dat        = utdc.load_config()
        self._d_sel    = cfg_dat['transformations']['selection']

        self._initialized = True
    # -------------------------------------------------------------------
    def _apply_selection(self, sel_kind : str) -> None:
        '''
        Loop over cuts and apply selection
        Save intermediate dataframes to self._d_rdf
        Save final datafrme to self._rdf
        '''
        # Skip selection if selection has not been implemented for current line
        if sel_kind is None:
            log.warning('Not applying selection')
            return

        rdf = self._rdf

        log.debug(f'Applying selection of kind {sel_kind}')
        d_cut    = self._d_sel['cuts']
        skip_cut = True
        for kind, cut in d_cut.items():
            # Skip selection if this block of cuts does not
            # correspond to current tree
            # any: Apply these cuts to any sample
            # sel_kind: Apply only if kind == sel_kind
            # This code will at most match two entried of d_cut

            if kind not in ['any', sel_kind]:
                continue

            skip_cut = False
            if len(cut) == 0:
                log.debug(f'Empty selection for kind: {sel_kind}')

            log.debug(90 * '-')
            log.debug(f'{"Cut":<20}{"Expression":<70}')
            log.debug(90 * '-')
            for name, cut_val in cut.items():
                log.debug(f'{name:<20}{cut_val:<70}')
                rdf = rdf.Filter(cut_val, f'{name}:{kind}')

            self._d_rdf[kind] = rdf

        if skip_cut:
            log.info(40 * '-')
            log.warning(f'sel_kind \"{sel_kind}\" not found among:')
            for kind in d_cut:
                log.info(f'    \"{kind}\"')
            log.info(40 * '-')

        self._rdf = rdf
    # --------------------------------------
    def _prescale(self):
        '''
        Will pick up a random subset of entries from the dataframe if 'prescale=factor' found in selection section
        '''

        if 'prescale' not in self._d_sel:
            log.debug('Not prescaling')
            return

        prs = self._d_sel['prescale']
        log.warning(f'Prescaling by a factor of: {prs}')

        rdf = self._rdf.Define('prs', f'gRandom->Integer({prs})')
        rdf = rdf.Filter('prs==0')

        self._rdf = rdf
    # -------------------------------------------------------------------
    def _evt_max(self):
        '''
        Will limit running to the first "evt_max" entries from the selection section
        '''

        if 'evt_max' not in self._d_sel:
            log.debug('Not limitting number of entries, no evt_max was found')
            return

        if self._d_sel['evt_max'] < 0:
            log.debug('Not limitting number of entries, found negative number for max_evt')
            return

        mevt = self._d_sel['evt_max']
        log.warning(f'Limitting to first: {mevt}')

        self._rdf = self._rdf.Filter(f'rdfentry_ < {mevt}')
    # -------------------------------------------------------------------
    def _print_info(self, rdf):
        log_lvl = log.level
        if log_lvl < 20:
            rep = rdf.Report()
            rep.Print()
    # -------------------------------------------------------------------
    def run(self, sel_kind : str, as_cutflow=False) -> Union[RDataFrame, dict[str,RDataFrame]]:
        '''
        Will return ROOT dataframe(s)

        Parameters
        -------------------
        sel_kind         : Type of selection, found in transformations/selection section of config
        as_cutflow (bool): If true will return {cut_name -> rdf} dictionary
        with cuts applied one after the other. If False (default), it will only return
        the dataframe after the full selection
        '''
        self._initialize()
        self._prescale()
        self._evt_max()

        self._apply_selection(sel_kind)

        d_rdf = { key : self._atr_mgr.add_atr(rdf) for key, rdf in self._d_rdf.items() }

        self._print_info(self._rdf)

        if as_cutflow:
            return d_rdf

        return self._rdf
# -------------------------------------------------------------------
