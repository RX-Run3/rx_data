'''
Script used to plot luminosity
'''
import numpy
import mplhep
import pandas            as pnd
import matplotlib.pyplot as plt

from typing    import Final
from ROOT      import RDataFrame
from rx_common import Campaign

# TODO: Clean this up
plt.style.use(mplhep.style.LHCb2)
_LUMI_PATH : Final[str] = '/home/acampove/Packages/lumi_calib/luminosity.root'
_LUMI_TREE : Final[str] = 'offline_lumi'
# ---------------------------------
def _get_df() -> pnd.DataFrame:
    rdf = RDataFrame(_LUMI_TREE, _LUMI_PATH)
    data= rdf.AsNumpy()
    df  = pnd.DataFrame(data)
    df  = df.sort_values(by='runNumber')

    df['lumi_up'] = df['lumi'] + df['lumi_error']
    df['lumi_dn'] = df['lumi'] - df['lumi_error']

    return df
# ---------------------------------
def _style_plot() -> None:
    plt.ylim(bottom=0)
    plt.xlabel('Run Number')
    plt.ylabel('Integrated Luminosity fb${}^{-1}$')
    plt.yscale('linear')
# ---------------------------------
def _add_lines() -> None:
    for campaign in Campaign:
        if campaign == Campaign.c1_24:
            continue

        start, _ = campaign.runs

        plt.axvline(
            x     = start, 
            lw    = 1.0,
            ls    = '-.',
            color = campaign.color, 
            label = campaign.name)
# ---------------------------------
def plot():
    '''
    Start here
    '''
    df_rx_all                = _get_df()
    df_rx_all['int_lumi_up'] = df_rx_all.lumi_up.cumsum() / 1_000_000_000
    df_rx_all['int_lumi_dn'] = df_rx_all.lumi_dn.cumsum() / 1_000_000_000
    rx_lumi                  = df_rx_all.lumi.sum()    / 1_000_000_000

    xval    : numpy.ndarray = df_rx_all['runNumber'  ].to_numpy()
    lumi_dn : numpy.ndarray = df_rx_all['int_lumi_dn'].to_numpy()
    lumi_up : numpy.ndarray = df_rx_all['int_lumi_up'].to_numpy()

    plt.fill_between(
        x     = xval, 
        y1    = lumi_dn, # type: ignore
        y2    = lumi_up, # type: ignore 
        color = 'gray', 
        alpha = 0.5,
        label = fr'Total: {rx_lumi:>4.2f} fb${{}}^{{-1}}$')

    _add_lines()
    _style_plot()
    plt.legend()
# ---------------------------------
