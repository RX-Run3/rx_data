'''
This module contains BaseFitter
'''
import json 
import textwrap

from pathlib     import Path
from dmu         import LogStore
from dmu.stats   import FitConf, FitResult, Fitter, ZFitPlotterConf
from dmu.stats   import utilities  as sut
from dmu.stats   import zfit
from zfit.data   import Data       as zdata
from zfit.pdf    import BasePDF    as zpdf
from rx_common   import Component, Qsq, Cuts
from rx_common   import Trigger

log  = LogStore.add_logger('fitter:base_fitter')
zobs = zfit.Space
# ------------------------
class BaseFitter:
    '''
    Fitting base class, meant to

    - Provide basic functionality to fiters for data and simulation
    - Behave as a dependency sink, avoiding circular imports
    '''
    # ------------------------
    def __init__(self):
        '''
        Used to hold attributes passed from derived classes
        '''
        self._q2bin     : Qsq
        self._trigger   : Trigger
        self._component : Component = Component.undefined
    # ------------------------
    def _fit(
        self,
        cfg   : FitConf,
        data  : zdata,
        model : zpdf) -> FitResult:
        '''
        Parameters
        --------------------
        cfg  : Fitting configuration
        data : Zfit data object
        model: Zfit PDF

        Returns
        --------------------
        Fit result object
        '''
        ftr = Fitter(pdf=model, data=data)
        res = ftr.fit(cfg=cfg)

        return res
    # ------------------------
    def _get_sensitivity(self, res : FitResult | None) -> float | None:
        '''
        Parameters
        --------------
        res: Result object from fit

        Returns
        --------------
        fit sensitivity in %
        '''
        if res is None:
            log.debug('Missing result object, cannot get sensitivity')
            return -1

        if not hasattr(self, '_trigger'):
            log.debug('No trigger found, not gettign sensitivity')
            return

        sig_name = self._trigger.project.signal_name
        if sig_name not in res:
            log.debug(f'Missing {sig_name} entry, cannot get sensitivity')
            log.debug(res)

            return None

        value, error = res[sig_name]

        sensitivity = 100 * error / value
        log.info(f'Found sensitivity: {sensitivity:.2f}')

        return sensitivity
    # --------------------------
    def _brem_cuts_from_cuts(self, cuts : dict[Cuts,str]) -> str:
        '''
        Parameters
        --------------
        cuts: Dictionary with cuts used for fit

        Returns
        --------------
        String with brem requirements
        '''
        l_brem_cut = []
        for cut in cuts.values():
            if 'nbrem' not in cut:
                continue
            l_brem_cut.append(cut)

        brem_cuts = '; '.join(l_brem_cut)

        return brem_cuts
    # --------------------------
    def _get_selection_diff(self, ini : dict[Cuts,str], fit : dict[Cuts,str]) -> str:
        '''
        Parameters
        -----------------
        ini: Initial (default) selection
        fit: Selection used for fit

        Returns
        -----------------
        Semicolon separated string with cuts that

        - Were modified from values in default
        - Were added on top of the default

        Cuts are never removed explicitly, just changed, e.g. mva > 0.3 ---> (1)
        '''
        s_ini = set(ini)
        s_fit = set(fit)

        s_intersection = s_ini & s_fit
        diff   = []
        for key in s_intersection:
            if ini[key] == fit[key]:
                continue

            diff.append(fit[key])

        for key in s_fit:
            if key in s_ini:
                continue

            diff.append(fit[key])

        return '\n'.join(diff)
    # --------------------------
    def _get_selection_text(self, selection : dict[str,dict[Cuts,str]]) -> tuple[str,str,str]:
        '''
        Parameters
        --------------
        selection: Object holding fitting and default selection
                   It should contain the fit and default selections in
                   the `fit` and `default` keys

        Returns
        --------------
        Tuple with:

        - Selection used for fit
        - Difference between fit selection and default 
        - Brem categories choice
        '''
        # For components like combinatorial, there is no MC sample
        # Therefore the selection or brem category does not make sense
        if self._component == Component.undefined:
            return '', '', ''

        cuts_ini : dict[Cuts,str] = selection['default']
        cuts_fit : dict[Cuts,str] = selection['fit'    ]

        sel_dif  = self._get_selection_diff(ini = cuts_ini, fit = cuts_fit)

        try:
            brem_cuts = self._brem_cuts_from_cuts(cuts=cuts_fit)
        except Exception as exc:
            raise ValueError('Cannot retrieve brem cut string from cuts dictionary') from exc

        sel_fit = json.dumps(cuts_fit, indent = 2)

        return sel_fit, sel_dif, brem_cuts
    # --------------------------
    def _entries_from_data(
        self, 
        data : zdata,
        obs  : zobs | None = None) -> int:
        '''
        Parameters
        ---------------
        data: Dataset used in the fit
        obs : Use this observable, if provided, otherwise use the one in data

        Returns
        ---------------
        Number of entries in data that were used for the fit,
        which are in the fit observable range
        '''
        used_obs = data.space if obs is None else obs

        [minx, maxx] = sut.range_from_obs(obs=used_obs)

        arr_mass = data.to_numpy()
        mask     = (minx < arr_mass) & (arr_mass < maxx)
        arr_mass = arr_mass[mask]
        nentries = len(arr_mass)

        return nentries
    # --------------------------
    def _get_text(
        self,
        data      : zdata,
        res       : FitResult | None,
        selection : dict[str,dict[Cuts,str]]) -> tuple[str,str,str]:
        '''
        Parameters
        --------------
        data     : Zfit data used for fit
        res      : Fit result object
        Selection: Object storing selections for `fit` and `default` keys

        Returns
        --------------
        Tuple with:

        - Title for fit plot
        - Text with full selection used in fit
        - Text that goes inside plot with selection information
        '''
        nentries                   = self._entries_from_data(data=data)
        sel_fit, sel_dif, brem_txt = self._get_selection_text(selection=selection)

        sensitivity = self._get_sensitivity(res=res)
        title       = f'Entries={nentries:.0f}'

        if sensitivity:
            title = f'{title}; $\\delta={sensitivity:.2f}$%'

        if brem_txt:
            title = f'{title}; Brem: {brem_txt}'

        return title, sel_fit, sel_dif
    # ------------------------
    def _save_fit(
        self,
        cut_cfg  : dict[str,dict[Cuts,str]],
        plt_cfg  : ZFitPlotterConf,
        out_path : Path,
        model    : zpdf      | None,
        res      : FitResult | None,
        data     : zdata,
        d_cns    : dict[str,tuple[float,float]]|None=None) -> None:
        '''
        Parameters
        --------------
        cut_cfg  : Selection used for fit in DictConfig object
                   Should contain keys `default` and `fit` the values
                   are the selection.
        plt_cfg  : Plotting configuration
        out_path : Directory where fit will be saved
        model    : PDF from fit, can be None if dataset was empty
        res      : Fit result object, can be None if fit was to get a KDE
        data     : data from fit
        d_cns    : Dictionary mapping parameter name to value error tuple.
                   Used for constraining that parameter
        '''
        # If no entries were present
        # There will not be PDF
        title, sel_fit, sel_dif = self._get_text(data=data, res=res, selection=cut_cfg)
        if plt_cfg.title:
            title = f'{plt_cfg.title}; {title}' 

        text       = '\n'.join(textwrap.wrap(sel_dif, width=40))
        new_fields = {'title' : title, 'ext_text' : text}
        plt_cfg    = plt_cfg.model_copy(update = new_fields)

        sel_path = out_path / 'selection.json'
        out_path.mkdir(parents = True, exist_ok = True)
        sel_path.write_text(sel_fit)

        sut.save_fit(
            data   = data,
            model  = model,
            res    = res,
            d_const= d_cns,
            plt_cfg= plt_cfg,
            fit_dir= out_path)
# ------------------------
