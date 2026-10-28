'''
This script will:

- Read a JSON file containing fitting parameters for fits to data and MC
- Transform them into JSON files with:
    parameters.json : The peak positions
    scales.json     : The scales

For each brem category and block

- Make plots of the peak positions and the scales
'''
import math
import argparse
import mplhep
import jacobi
import matplotlib.pyplot     as plt
import pandas                as pnd

from dmu             import LogStore
from dmu.generic     import utilities        as gut
from typing          import Callable, Final
from matplotlib.axes import Axes
from fitter          import FitSummarizer, MVAWp
from rx_q2           import ScalesConf
from rx_q2           import ParameterReader
from fitter          import ParameterReader as FitParameterReader
from rx_common       import Block, Channel, Correction
from rx_common       import Trigger, Component
from rx_common       import Qsq
from rx_common       import Brem

log=LogStore.add_logger('rx_q2:dump_q2_ratios')

_FRACTIONS : Final[list[str]]         = ['fr']
_DATA      : Component                = Component.data_24
_KIND      : Final[str]               = 'reso'              # All fits used for scales are to resonant mode
_BREMS     : dict[Channel,list[Brem]] = { Channel.ee : [Brem.one, Brem.two], Channel.mm : [Brem.zero] }
_Q2BIN     : Final[Qsq]               = Qsq.jpsi
#-------------------------------------
def _load_config(args : argparse.Namespace) -> ScalesConf:
    '''
    Returns
    -------------
    config class
    '''
    data         = gut.load_data(package='rx_q2_data', fpath=f'plots/scales_{args.kind}.yaml')
    data['kind'] = args.kind
    data['comb'] = args.comb
    data['prec'] = args.prec
    data['year'] = args.year
    data['trig'] = args.trig
    data['name'] = args.name

    cfg = ScalesConf(**data)

    return cfg
#-------------------------------------
# TODO: This is too hardcoded
def _get_Bx_df(cfg : ScalesConf) -> pnd.DataFrame:
    '''
    Parameters
    -----------------
    cfg: Object holding configuration

    Returns
    -----------------
    Pandas dataframe with mu, sg, fr, block, MVA wp
    '''
    trigger= cfg.trig
    signal = trigger.reso_jpsi_signal
    channel= trigger.channel
    blocks = Block.blocks()
    comps  = [_DATA, signal]

    smr= FitSummarizer(name = cfg.name, kind = _KIND)
    smr.get_summary(
        force_update = True, 
        out_name     = f'fit_summary_{cfg.comb.name}_{cfg.prec.name}.json')

    if not smr.output_path:
        raise ValueError('Output path not found')

    with FitParameterReader.inputs_from(pars_path = smr.output_path):
        rdr = FitParameterReader()

    l_data = []
    for brem in _BREMS[channel]:
        for block in blocks:
            for comp in comps:
                msr = rdr(
                    brem    = brem,
                    block   = block,
                    cmb     = cfg.comb,
                    prc     = cfg.prec,
                    comp    = comp,
                    trigger = trigger,
                    q2bin   = _Q2BIN)

                mu_val, mu_err = msr.get_par(prefix = f'mu_{signal}_{brem}').data
                sg_val, sg_err = msr.get_par(prefix = f'sg_{signal}_{brem}').data
                if not comp.is_mc:
                    bk_val, bk_err = msr.get_par(prefix = f'bk_{signal}_{brem}').data
                else:
                    bk_val, bk_err = 1.0, 0.0

                if channel == Channel.mm:
                    fr_val, fr_err = 0.001, 0.0 # Brem fraction for brem 1 is zero in muon channel 
                else:
                    fr_val, fr_err = msr.get_par(prefix = f'fr_{signal}_{brem}').data

                data = {
                    'mu_val' : mu_val,
                    'mu_err' : mu_err,
                    # ---
                    'sg_val' : sg_val,
                    'sg_err' : sg_err,
                    # ---
                    'fr_val' : fr_val,
                    'fr_err' : fr_err,
                    # ---
                    'bk_val' : bk_val,
                    'bk_err' : bk_err,
                    # ---
                    'block'  : block.value,
                    'brem'   : brem.to_int(),
                    'sample' : comp,
                }

                l_data.append(data)

    return pnd.DataFrame(l_data)
#-------------------------------------
def _get_q2_df(
    cfg    : ScalesConf,
    sample : str | None = None) -> pnd.DataFrame:
    '''
    Arguments
    --------------
    sample : dat or sim
    '''
    if sample is None:
        df_dat = _get_q2_df(cfg = cfg, sample = 'dat')
        df_dat['sample'] = 'dat'

        df_sim = _get_q2_df(cfg = cfg, sample = 'sim')
        df_sim['sample'] = 'sim'

        return pnd.concat([df_dat, df_sim], axis=0, ignore_index=True)

    path_wc = cfg.inp_dir / f'{sample}/{cfg.trig.project}_{cfg.year}'
    l_path  = list(path_wc.glob(pattern = '*/parameters.json'))
    nfiles  = len(l_path)

    df = pnd.DataFrame(columns=['mu_val', 'mu_err', 'sg_val', 'sg_err', 'brem', 'block'])
    if nfiles == 0:
        raise ValueError(f'Cannot find any parameters file in: {path_wc}')

    log.info(f'Found {nfiles} parameters files')

    rdr = ParameterReader(cfg = cfg)
    for path in l_path:
        df.loc[len(df)] = rdr.read(path=path)

    return df
#-------------------------------------
def _get_scales(
    df     : pnd.DataFrame,
    signal : Component,
    cfg    : ScalesConf) -> pnd.DataFrame:
    '''
    Parameters
    ---------------
    df    : Pandas dataframe with fitting parameters, e.g. mu, sg.
    signal: Signal component
    cfg   : Configuration

    Returns
    ---------------
    Pandas dataframe with scales and resolutions, columns:

    smu_val   smu_err   ssg_val   ssg_err  block  brem
    '''
    l_df_scale : list[pnd.DataFrame] = []
    for (block, brem), df_group in df.groupby(['block', 'brem']):
        sblock = str(block)
        iblock = int(sblock)

        sbrem  = str(brem)
        ibrem  = int(sbrem)

        df_scale          = _scales_from_df(df=df_group, signal = signal)
        df_scale['block'] = iblock
        df_scale['brem' ] = ibrem

        l_df_scale.append(df_scale)

    if not l_df_scale:
        raise ValueError('No dataframes found to concatenate')

    df = pnd.concat(l_df_scale, ignore_index=True)
    df.to_json(cfg.out_dir / 'scales.json', indent = 2)

    return df
#-------------------------------------
def _reorder_blocks(df : pnd.DataFrame) -> pnd.DataFrame:
    custom_order = ['0', '4', '3', '1', '2', '1', '5', '6', '7', '8']
    df['block']  = df['block'].astype(str)

    order_map = {val: i for i, val in enumerate(custom_order)}
    df['order'] = df['block'].map(order_map)

    df= df.sort_values('order')

    return df
#-------------------------------------
def _scales_from_df(
    signal : Component,
    df     : pnd.DataFrame) -> pnd.DataFrame:
    '''
    Parameters
    ------------------
    signal: Signal component
    df    : Dataframe with fit parameters

    Returns
    ------------------
    Dataframe with corrections
    '''
    d_mu = _get_scale(df=df, corr= Correction.mass_scale     , signal = signal, fun=lambda x : x[0] - x[1])
    d_sg = _get_scale(df=df, corr= Correction.mass_resolution, signal = signal, fun=lambda x : x[0] / x[1])
    d_fr = _get_scale(df=df, corr= Correction.brem_fraction  , signal = signal, fun=lambda x : x[0] / x[1])

    corr     = Correction.blok_fraction
    df_dat   = df.query(f'sample == \"{_DATA}\"')
    val, err = _get_entry(corr=corr, df=df_dat, comp = _DATA)
    d_bk     = {f'{corr}_val' : [val], f'{corr}_err' : [err]}

    df   = pnd.DataFrame({**d_mu, **d_sg, **d_fr, **d_bk})

    return df
#-------------------------------------
def _get_scale(
    df     : pnd.DataFrame,
    signal : Component,
    corr   : Correction,
    fun    : Callable) -> dict[str,list[float]]:
    '''
    Parameters
    ------------------
    df    : Dataframe with mass scales and resolutions
    corr  : Variable whose scale or resolution will be calculated
    fun   : Function used to calculate scale or resolution
    signal: Signal componnt

    Returns
    ------------------
    Dictionary mapping:

    key  : Name of scale/resolution
    value: Numerical value
    '''
    df_dat  = df.query(f'sample == \"{_DATA}\"')
    df_sim  = df.query(f'sample == \"{signal}\"')

    dat_val, dat_err = _get_entry(corr=corr, df=df_dat, comp = _DATA)
    sim_val, sim_err = _get_entry(corr=corr, df=df_sim, comp = signal)

    cov : list[list[float]] = [
        [dat_err ** 2,            0],
        [0           , sim_err ** 2]]

    vals     = [dat_val, sim_val]
    val, var = jacobi.propagate(fun, vals, cov) # type: ignore
    val      = float(val)
    err      = math.sqrt(var)

    match corr:
        case Correction.mass_scale:
            return {f'{corr}_val' : [val], f'{corr}_err' : [err]}
        case Correction.mass_resolution:
            return {f'{corr}_val' : [val], f'{corr}_err' : [err]}
        case Correction.brem_fraction:
            return {f'{corr}_val' : [val], f'{corr}_err' : [err]}
        case _:
            raise ValueError(f'Invalid correction: {corr}')
# ----------------------
def _get_entry(
    corr : Correction,
    comp : Component,
    df   : pnd.DataFrame) -> tuple[float,float]:
    '''
    Parameters
    -------------
    corr: Correction used
    df  : DataFrame with scales and resolutions

    Returns
    -------------
    Tuple with value and error
    '''
    if len(df) != 1:
        log.error(df)
        raise ValueError(f'Expected one and only one row for correction: {corr}/{comp}')

    try:
        val = df[f'{corr.var}_val'].iloc[0]
        err = df[f'{corr.var}_err'].iloc[0]
    except Exception as exc:
        log.error('\n' + str(df))
        raise ValueError(f'Cannot find value or error of {corr}') from exc

    return val, err
#-------------------------------------
def _plot_df(
    df       : pnd.DataFrame,
    variable : str,
    brem     : Brem,
    ax       : Axes) -> Axes:

    val   = f'{variable}_val'
    err   = f'{variable}_err'

    try:
        low = df[val] - df[err]
        high= df[val] + df[err]

        ax.fill_between(
            x    = df['block'],
            y1   = low.to_numpy(dtype=float), # type: ignore
            y2   = high.to_numpy(dtype=float),# type: ignore
            color= brem.color,
            label= brem.latex,
            alpha= 0.5)
    except TypeError as exc:
        log.error(df)
        log.error(df.dtypes)
        raise TypeError('Cannot plot data in dataframe') from exc

    return ax
#-------------------------------------
def _plot_corrections(
    df         : pnd.DataFrame,
    cfg        : ScalesConf,
    correction : Correction) -> None:

    log.info(f'Plotting correction: {correction}')

    _, ax = plt.subplots(figsize=(15, 10))
    for val, df_brem_unordered in df.groupby('brem'):
        df_brem = _reorder_blocks(df=df_brem_unordered)
        sval    = str(val)

        if sval != '2' and correction == Correction.brem_fraction:
            continue

        brem    = Brem.from_str(value = f'xx{sval}')
        ax      = _plot_df(df=df_brem, variable=correction, brem=brem, ax=ax)

    if correction != Correction.brem_fraction:
        ax.legend()

    rng = cfg.get_range(var=correction)

    plt.ylabel(correction.latex)
    plt.ylim(rng)
    plt.grid()
    plt.savefig(cfg.out_dir / f'{correction}.png')
    plt.close()
#-------------------------------------
def _plot_variables(
    df       : pnd.DataFrame,
    cfg      : ScalesConf,
    variable : str,
    comp     : Component) -> None:
    '''
    Parameters
    -----------------
    comp: Component, e.g. data, bpkpee
    '''
    log.info(f'Plotting {variable} for {comp}')
    _, ax = plt.subplots(figsize=(15, 10))
    for val, df_brem_unordered in df.groupby('brem'):
        sval    = str(val)

        # Block and brem fractions only make sense for brem one
        # and are the same for both brems
        if variable in _FRACTIONS and sval == '2':
            log.debug(f'Skipping {sval}/{variable}')
            continue

        brem    = Brem.from_str(value = f'xx{sval}')
        df_brem = _reorder_blocks(df = df_brem_unordered)
        ax      = _plot_df(df=df_brem, variable=variable, brem=brem, ax=ax)

    # Fractions only make sense for either
    # one brem category or both combined
    # label makes no sense
    if variable not in _FRACTIONS:
        plt.legend()
    else:
        plt.legend(labels = [])

    latex = 'MC' if comp.is_mc else 'Data'

    if   variable == 'mu':
        plt.ylabel(rf'$\mu^{{{latex}}}$[MeV]')
        ax.axhline(y=cfg.pdg_mass, color='black', linestyle=':', label='PDG')
    elif variable == 'sg':
        plt.ylabel(rf'$\sigma^{{{latex}}}$[MeV]')
    elif variable == 'fr':
        plt.ylabel(rf'$fr_{{Brem}}^{{{latex}}}$[MeV]')
    elif variable == 'bk':
        plt.ylabel(rf'$fr_{{Block}}^{{{latex}}}$[MeV]')
    else:
        raise ValueError(f'Invalid variable: {variable}')

    rng = cfg.get_range(var=variable)
    plt.ylim(rng)
    plt.grid()
    plt.savefig(cfg.out_dir / f'{variable}_{comp}.png')
    plt.close()
#-------------------------------------
def _plot(
    df  : pnd.DataFrame,
    cfg : ScalesConf) -> None:
    '''
    Parameters
    ---------------
    df: Pandas dataframe with fitting parameters, e.g. mu, sg.
    '''
    signal : Component | None = None
    for kind, df_kind in df.groupby('sample'):
        comp = Component(kind)

        _plot_variables(df=df_kind, variable='mu', comp = comp, cfg = cfg)
        _plot_variables(df=df_kind, variable='sg', comp = comp, cfg = cfg)
        _plot_variables(df=df_kind, variable='fr', comp = comp, cfg = cfg)

        if not comp.is_mc:
            _plot_variables(df=df_kind, variable='bk', comp = comp, cfg = cfg)

        if comp != _DATA:
            signal = comp

    if signal is None:
        raise ValueError('Signal component not found')

    df_scale = _get_scales(df = df, cfg = cfg, signal = signal)
    _plot_corrections(df=df_scale, cfg = cfg, correction=Correction.mass_resolution)
    _plot_corrections(df=df_scale, cfg = cfg, correction=Correction.mass_scale)
    _plot_corrections(df=df_scale, cfg = cfg, correction=Correction.brem_fraction)
#-------------------------------------
def _get_df(cfg : ScalesConf) -> pnd.DataFrame:
    '''
    Parameters
    -----------
    cfg: Configuration needed to get scales

    Returns
    -----------
    Dataframe with fitting parameters, e.g. mu, sg
    '''
    if   cfg.kind == 'q2':
        df = _get_q2_df(cfg = cfg)
    elif cfg.kind ==  'B':
        df = _get_Bx_df(cfg = cfg)
    else:
        raise ValueError(f'Invalid kind: {cfg.kind}')

    return df
#-------------------------------------
def main():
    '''
    Entry point
    '''
    parser = argparse.ArgumentParser(description='Used to create pandas dataframe with information from fits needed to smear q2')
    parser.add_argument('-k', '--kind'   , type=str           , help='Type of scales'   , required=True, choices=['q2', 'B'])
    parser.add_argument('-C', '--comb'   , type=MVAWp.from_str, help='Combinatorial WP' , required=True)
    parser.add_argument('-P', '--prec'   , type=MVAWp.from_str, help='Part reco WP'     , required=True)
    parser.add_argument('-t', '--trig'   , type=Trigger       , help='Name of trigger'  , required=True)
    parser.add_argument('-n', '--name'   , type=str           , help='Name of fits'     , required=True)
    parser.add_argument('-y', '--year'   , type=str           , help='Year for data whose corrections are needed', default='2024')
    args = parser.parse_args()

    plt.style.use(mplhep.style.LHCb2)

    cfg  = _load_config(args = args)

    out_path = cfg.out_dir / 'parameters.json'
    if out_path.exists():
        log.warning(f'Dataframe already found, reusing: {out_path}')
        df = pnd.read_json(out_path)

        _plot(df=df, cfg = cfg)

        return

    log.info(f'Dataframe with parameters not found making: {out_path}')
    df = _get_df(cfg = cfg)
    df.to_json(out_path, indent=2)

    _plot(df=df, cfg = cfg)
#-------------------------------------
if __name__ == '__main__':
    main()
