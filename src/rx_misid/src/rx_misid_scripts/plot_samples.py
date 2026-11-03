'''
This script is meant to:

- Plot pT and Eta distributions with and without PID weights in brem categories
- Plot map overlaid to countour plots of misID samples

where the misID samples are B-> KKK and B -> Kpipi
'''
import os
import argparse

import tqdm
import numpy
import mplhep
import seaborn           as sns
import pandas            as pnd
import matplotlib.pyplot as plt

from dataclasses              import dataclass, field
from pathlib                  import Path
from rx_common                import Component, Cuts, Qsq
from typing                   import Final
from omegaconf                import DictConfig, OmegaConf
from rx_data.rdf_getter       import RDFGetter
from rx_misid.sample_splitter import SampleSplitter
from rx_misid.sample_weighter import SampleWeighter
from dmu.logging.log_store    import LogStore
from rx_selection             import selection  as sel
from boost_histogram          import Histogram  as bh
from dmu.generic              import utilities  as gut
from dmu.workflow.cache       import Cache      as Wcache

log=LogStore.add_logger('rx_misid:plot_samples')
_MAX_EFF : Final[float] = 100
# ----------------------
@dataclass
class PlotConfig:
    particle : str

    SAMPLES  = ['Bu_piplpimnKpl_eq_sqDalitz_DPC', 'Bu_KplKplKmn_eq_sqDalitz_DPC']
    PARTICLES= ['kaon', 'pion']
    BLOCKS   = [1, 2, 3, 4, 5, 6, 7, 8]
    BREMCATS = ['nobrem', 'brem']
    REGIONS  = ['signal', 'control']
    Q2BINS   = ['low', 'central', 'high']

    nplots   : int        = field(init=False)
    block    : int        = field(init=False)
    sample   : str        = field(init=False)
    q2bin    : str        = field(init=False)
    bremcat  : str        = field(init=False)
    region   : str        = field(init=False)

    rdf_cfg  : dict       = field(init=False)
    weighter : DictConfig = field(init=False)
    splitter : DictConfig = field(init=False)
    # ----------------------
    def __post_init__(self):
        cfg      = gut.load_conf(package='rx_misid_data', fpath='sample_plotting.yaml')
        this_dir = Path(os.getcwd())
        Wcache.set_cache_root(root =this_dir / '.cache')

        self._build_rdf_getter(cfg=cfg)
        self.weighter = cfg.wgt_cfg
        self.splitter = cfg.spl_cfg
    # ----------------------
    def calculate_plots(self) -> None:
        '''
        Calculates number of plots to be make
        and assigns them to self.nplots
        '''
        nplots = 1
        if self.block   ==    -1:
            nplots *= len(self.BLOCKS)

        if self.sample  == 'all':
            nplots *= len(self.SAMPLES)

        if self.q2bin   == 'all':
            nplots *= len(self.Q2BINS)

        if self.bremcat == 'all':
            nplots *= len(self.BREMCATS)

        if self.region  == 'all':
            nplots *= len(self.REGIONS)

        self.nplots = nplots
    # ----------------------
    @staticmethod
    def sample_from_particle(particle : str) -> str:
        '''
        Transform nickname into actual sample name
        '''
        if particle == 'all':
            return 'all'

        if particle == 'kaon':
            return 'Bu_KplKplKmn_eq_sqDalitz_DPC'

        if particle == 'pion':
            return 'Bu_piplpimnKpl_eq_sqDalitz_DPC'

        raise NotImplementedError(f'Invalid particle: {particle}')
    # ----------------------
    @staticmethod
    def particle_from_sample(sample : str) -> str:
        '''
        Transform sample into nickname
        '''
        if sample == 'all':
            return 'all'

        if sample == 'Bu_KplKplKmn_eq_sqDalitz_DPC':
            return 'kaon'

        if sample == 'Bu_piplpimnKpl_eq_sqDalitz_DPC':
            return 'pion'

        raise NotImplementedError(f'Invalid sample: {sample}')
    # ----------------------
    def _build_rdf_getter(self, cfg : DictConfig) -> None:
        '''
        Parameters
        -------------
        cfg : Configuration from yaml, needed to update current class
        '''
        d_cfg      = OmegaConf.to_container(cfg.rdf_getter, resolve=True)
        if not isinstance(d_cfg, dict):
            raise TypeError('Config is not a dictionary')

        self.sample  = self.sample_from_particle(particle=self.particle)
        self.rdf_cfg = d_cfg
# ----------------------
def _parse_args() -> PlotConfig:
    parser = argparse.ArgumentParser(description='Script used to make diagnostic plots')
    parser.add_argument('-p', '--particle', type=str, help='Particle'                , choices=PlotConfig.PARTICLES, default='all')
    parser.add_argument('-r', '--region'  , type=str, help='Region associated to map', choices=PlotConfig.REGIONS  , default='all')
    parser.add_argument('-q', '--q2bin'   , type=str, help='Q2 bin'                  , choices=PlotConfig.Q2BINS   , default='all')
    parser.add_argument('-B', '--bremcat' , type=str, help='Brem category'           , choices=PlotConfig.BREMCATS , default='all')
    parser.add_argument('-b', '--block'   , type=int, help='Block'                   , choices=PlotConfig.BLOCKS   , default=   -1)
    parser.add_argument('-l', '--log_lvl' , type=int, help='Logging level'           , choices=[10, 20, 30, 40, 50], default=   20)
    args = parser.parse_args()

    cfg         = PlotConfig(particle=args.particle)
    cfg.region  = args.region
    cfg.q2bin   = args.q2bin
    cfg.bremcat = args.bremcat
    cfg.block   = args.block
    cfg.calculate_plots()

    _set_logs(level = args.log_lvl)

    return cfg
# ----------------------
def _set_logs(level : int) -> None:
    '''
    Parameters
    -------------
    level: Logging level
    '''
    LogStore.set_level('rx_selection:selection'     ,    30)
    LogStore.set_level('rx_selection:truth_matching',    30)
    LogStore.set_level('rx_data:rdf_getter'         ,    30)
    LogStore.set_level('rx_misid:sample_splitter'   ,    40)
    LogStore.set_level('rx_misid:sample_weighter'   ,    30)
    LogStore.set_level('rx_misid:plot_samples'      , level)
# ----------------------
def _get_df(
    cfg    : PlotConfig,
    q2bin  : Qsq,
    sample : Component,
    region : str) -> pnd.DataFrame:
    '''
    Parameters
    -------------
    cfg   : Configuration needed to make dataframe
    q2bin : E.g. central
    sample: MC sample, e.g. mc_bukee...
    region: signal or control

    Returns
    -------------
    Pandas dataframe with PID weighted sample
    '''
    gtr   = RDFGetter(**cfg.rdf_cfg, sample=sample)
    rdf   = gtr.get_rdf(per_file=False)
    uid   = gtr.get_uid()
    cuts  = {
        Cuts.pid_l : '(1)',
        Cuts.brem  : 'nbrem != 0'} # Do not care about brem 0 candidates

    with sel.custom_selection(d_sel = cuts):
        rdf = sel.apply_full_selection(
            rdf    = rdf,
            uid    = uid,
            q2bin  = q2bin,
            process= sample,
            trigger= cfg.rdf_cfg['trigger'])

    out_dir = Path('misid')
    spl   = SampleSplitter(
        rdf     = rdf,
        cfg     = cfg.splitter,
        out_dir = out_dir)
    df    = spl.get_sample()

    wgt   = SampleWeighter(
        df    = df,
        cfg   = cfg.weighter,
        sample= sample,
        is_sig= region == 'signal')
    df  = wgt.get_weighted_data()

    return df
# ----------------------
def _plot_overlay(
    df     : pnd.DataFrame,
    hist   : bh,
    key    : str,
    bremcat: str,
    cfg    : PlotConfig) -> None:
    '''
    Parameters
    -------------
    df     : DataFrame with data to be plotted
    bh     : Histogram with calibration map
    key    : Map identifier
    cfg    : Configuration to make plots
    bremcat: brem or nobrem
    '''
    arr_pt = _get_array(df=df, quantity='TRACK_PT' , bremcat=bremcat)
    arr_et = _get_array(df=df, quantity='TRACK_ETA', bremcat=bremcat)
    arr_pt = numpy.log10(arr_pt)

    levels = [0.68, 0.95, 0.997]
    styles = ['dotted', 'dashed', 'solid']

    _plot_map(hist=hist)
    for level, style in zip(levels, styles, strict=True):
        sns.kdeplot(
            x         =arr_pt,
            y         =arr_et,
            levels    =[1 - level],
            c         ='red',
            lw        =0.5,
            linestyles=style)

    plot_path = _get_map_path(key=key, cfg=cfg)
    plt.title(f'{key}; Entries={len(df)}')
    plt.xlabel(r'$\log_{10}(p_T)$ MeV')
    plt.ylabel(r'$\eta$')
    plt.xlim(2.0, 5.0)
    plt.ylim(1.5, 5.5)
    plt.savefig(plot_path)
    plt.close()
# ----------------------
def _get_map_path(key : str, cfg : PlotConfig) -> Path:
    '''
    Parameters
    -------------
    key: Identifier of map been saved
    cfg: Configuration object

    Returns
    -------------
    Path to PNG file
    '''
    maps_path = Path(cfg.weighter.maps_path)
    ana_dir   = os.environ['ANADIR']
    out_dir   =ana_dir/maps_path/'coverage'
    out_dir.mkdir(exist_ok=True)

    return out_dir/f'{key}.png'
# ----------------------
def _plot_map(hist : bh) -> None:
    '''
    Parameters
    -------------
    hist: Calibration map
    '''
    x_edges      = hist.axes[0].edges
    y_edges      = hist.axes[1].edges
    bin_values   = hist.view()['value']
    if not isinstance(bin_values, numpy.ndarray):
        raise TypeError('Bin values not a numpy array')

    arr_x, arr_y = numpy.meshgrid(x_edges, y_edges)

    counts  = 100 * bin_values
    tmp     = numpy.where((counts < _MAX_EFF) & (counts >= 0), counts, 0)
    maxz    = numpy.max(tmp)
    plt.pcolormesh(arr_x, arr_y, counts.T, shading='auto', vmin=0, vmax=maxz)
    plt.colorbar(label='Efficiency [%]')
# ----------------------
def _get_array(
    df       : pnd.DataFrame,
    quantity : str,
    bremcat  : str) -> numpy.ndarray:
    '''
    Parameters
    -------------
    df      : DataFrame with data to be plotted
    quantity: E.g. PT
    bremcat : E.g. nobrem

    Returns
    -------------
    Array of `quantity` for L1 and L2
    '''
    cat = {'nobrem' : 0, 'brem' : 1}[bremcat]

    df_l1 = df[ df['L1_HASBREM'] == cat ]
    name  = 'pid_eff_l1' if quantity == 'weight' else f'L1_{quantity}'
    arr_l1= df_l1[name].to_numpy()

    df_l2 = df[ df['L2_HASBREM'] == cat ]
    name  = 'pid_eff_l2' if quantity == 'weight' else f'L2_{quantity}'
    arr_l2= df_l2[name].to_numpy()

    return numpy.concatenate((arr_l1, arr_l2))
# ----------------------
def main():
    '''
    Entry point
    '''
    mplhep.style.use('LHCb2')
    cfg = _parse_args()

    d_hist= {}
    d_hist.update(SampleWeighter.get_maps(cfg=cfg.weighter, kind=  'brem'))
    d_hist.update(SampleWeighter.get_maps(cfg=cfg.weighter, kind='nobrem'))

    pbar = tqdm.tqdm(total=cfg.nplots, ascii=' -')

    for bremcat in PlotConfig.BREMCATS:
        if cfg.bremcat not in ['all', bremcat]:
            log.debug(f'Skip {bremcat}')
            continue

        for region in PlotConfig.REGIONS:
            if cfg.region not in ['all', region]:
                log.debug(f'Skip {region}')
                continue

            for q2bin in PlotConfig.Q2BINS:
                if cfg.q2bin not in ['all', q2bin]:
                    log.debug(f'Skip {q2bin}')
                    continue

                for sample in PlotConfig.SAMPLES:
                    if cfg.sample not in ['all', sample]:
                        log.debug(f'Skip {sample}')
                        continue

                    df  = _get_df(cfg=cfg, region=region, q2bin=q2bin, sample=sample)
                    for block in PlotConfig.BLOCKS:
                        if cfg.block not in [-1, block]:
                            log.debug(f'Skip {block}')
                            continue

                        particle  = PlotConfig.particle_from_sample(sample=sample)
                        df_block  = df[df['block'] == block]
                        key       = f'block{block}_{particle}_{region}'
                        hist      = d_hist[key]

                        log.debug(f'Plotting block: {block}')
                        _plot_overlay(df=df_block, cfg=cfg, hist=hist, bremcat=bremcat, key=f'{key}_{bremcat}_{q2bin}')
                        pbar.update(1)
# ----------------------
if __name__ == '__main__':
    main()
