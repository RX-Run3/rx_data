'''
Module containing Plotter2D class
'''
from typing import Union

import hist
import numpy
import mplhep
import matplotlib.pyplot as plt

from hist               import Hist
from ROOT               import RDF
from matplotlib.colors  import LogNorm
from dmu                import LogStore
from .plotter           import Plotter

log = LogStore.add_logger('dmu:plotting:Plotter2D')
# --------------------------------------------
class Plotter2D(Plotter):
    '''
    Class used to plot columns in ROOT dataframes
    '''
    # --------------------------------------------
    def __init__(self, rdf=None, cfg=None):
        '''
        Parameters:

        d_rdf (dict): Dictionary mapping the kind of sample with the ROOT dataframe
        cfg   (dict): Dictionary with configuration, e.g. binning, ranges, etc
        '''

        super().__init__({'single_rdf' : rdf}, cfg)
        self._rdf : RDF.RNode = self._d_rdf['single_rdf']

        self._wgt : numpy.ndarray
    # --------------------------------------------
    def _get_axis(self, var : str):
        [minx, maxx, nbins] = self._cfg['axes'][var]['binning']
        label               = self._cfg['axes'][var][  'label']

        axis = hist.axis.Regular(nbins, minx, maxx, name=label, label=label)

        return axis
    # --------------------------------------------
    def _get_data(self, varx : str, vary : str) -> tuple[numpy.ndarray, numpy.ndarray]:
        d_data = self._rdf.AsNumpy([varx, vary])
        arr_x  = d_data[varx]
        arr_y  = d_data[vary]

        return arr_x, arr_y
    # --------------------------------------------
    def _get_dataset_weights(self, wgt_name : Union[str, None]) -> Union[numpy.ndarray, None]:
        if wgt_name is None:
            log.debug('Skipping weights')
            return None

        log.debug(f'Adding weights form column {wgt_name}')
        arr_wgt  = self._rdf.AsNumpy([wgt_name])[wgt_name]

        return arr_wgt
    # --------------------------------------------
    def _plot_vars(self, varx : str, vary : str, wgt_name : str, use_log : bool) -> None:
        log.info(f'Plotting {varx} vs {vary} with weights {wgt_name}')

        ax_x         = self._get_axis(varx)
        ax_y         = self._get_axis(vary)
        arr_x, arr_y = self._get_data(varx, vary)

        arr_w = self._get_dataset_weights(wgt_name)
        hst   = Hist(ax_x, ax_y)
        hst.fill(arr_x, arr_y, weight=arr_w)

        if hst.values().sum() == 0:
            log.warning('Empty histogram, not using log scale')
            mplhep.hist2dplot(hst)
            return

        if use_log:
            mplhep.hist2dplot(hst, norm=LogNorm())
        else:
            mplhep.hist2dplot(hst)
    # --------------------------------------------
    def run(self):
        '''
        Will run plotting
        '''

        fig_size = self._get_fig_size()
        for [varx, vary, wgt_name, plot_name, use_log] in self._cfg['plots_2d']:
            fig, _= plt.subplots(figsize=fig_size)
            self._plot_vars(varx, vary, wgt_name, use_log)
            self._save_plot(var=plot_name, fig=fig)
# --------------------------------------------
