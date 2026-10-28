'''
Script used to plot binned quantities
'''
import os
import json
import argparse
from importlib.resources import files
from functools           import lru_cache

import yaml
import numpy
import matplotlib.pyplot as plt
from ROOT                    import RDataFrame, EnableImplicitMT
from dmu.logging.log_store   import LogStore
from rx_data.rdf_getter      import RDFGetter
from rx_selection            import selection as sel

log=LogStore.add_logger('rx_plotter:binned')
# -----------------------------
class Data:
    '''
    data class
    '''
    conf_name : str
    cfg       : dict
    d_bound   : dict[str,list[str]] = {}
    cache_dir = '/tmp/rx_plotter/cache'

    os.makedirs(cache_dir, exist_ok=True)
# -----------------------------
def _parse_args():
    parser = argparse.ArgumentParser(description='Used to plot 2D distributions')
    parser.add_argument('-c', '--conf' , type=str, help='Name of config file')
    args = parser.parse_args()

    Data.conf_name = args.conf
# -----------------------------
def _load_config() -> None:
    conf_path = files('rx_plotter_data').joinpath(f'binned/{Data.conf_name}.yaml')
    with open(conf_path, encoding='utf-8') as ifile:
        Data.cfg = yaml.safe_load(ifile)
# -----------------------------
@lru_cache
def _get_rdf() -> RDataFrame:
    q2bin   = Data.cfg['input']['q2bin']
    trigger = Data.cfg['input']['trigger']
    sample  = Data.cfg['input']['sample']
    ncores  = Data.cfg['processing']['ncores']
    if ncores > 1:
        EnableImplicitMT(ncores)

    RDFGetter.samples = Data.cfg['input']['samples']
    gtr = RDFGetter(sample=sample, trigger=trigger)
    rdf = gtr.get_rdf()

    d_sel = sel.selection(project='RK', analysis='EE', q2bin=q2bin, process=sample)
    d_cut = Data.cfg['cuts']
    d_sel.update(d_cut)

    for cut_name, cut_value in d_sel.items():
        log.info(f'{cut_name:<20}{cut_value}')
        rdf = rdf.Filter(cut_value, cut_name)

    return rdf
# -----------------------------
def _get_bounds(var_name : str, d_bin : dict, isobin : bool) -> list[float]:
    if var_name in Data.d_bound:
        return Data.d_bound[var_name]

    nbin    = d_bin['nbin']
    minx    = d_bin['min' ]
    maxx    = d_bin['max' ]

    if isobin:
        arr_bound = numpy.linspace(minx, maxx, nbin + 1)
        l_bound   = arr_bound.tolist()
        Data.d_bound[var_name] = l_bound

        return l_bound

    rdf     = _get_rdf()
    rdf     = rdf.Filter(f'({var_name} > {minx}) && ({var_name} < {maxx})')
    arr_val = rdf.AsNumpy([var_name])[var_name]

    arr_qnt = numpy.linspace(0, 1, nbin + 1)
    arr_bnd = numpy.quantile(arr_val, arr_qnt)
    l_bound = arr_bnd.tolist()

    Data.d_bound[var_name] = l_bound

    return l_bound
# -----------------------------
def _cuts_from_binning(l_name : list[str], l_setting : list, index : int) -> list[str]:
    var_name = l_name[index]
    d_bin    = l_setting[index]['binning']
    isobin   = l_setting[index]['isobin' ]

    l_bound  = _get_bounds(var_name, d_bin, isobin)
    l_min    = l_bound[:-1]
    l_max    = l_bound[+1:]

    l_cut = [ f'({var_name} > {minv:>3.0f}) && ({var_name} <={maxv:>3.0f})' for minv, maxv in zip(l_min, l_max)]

    return l_cut
# -----------------------------
def _get_full_stats(rdf: RDataFrame, var_name : str) -> tuple[float,float]:
    arr_val = rdf.AsNumpy([var_name])[var_name]
    nval    = len(arr_val)
    val     = numpy.std(arr_val)
    err     = val / numpy.sqrt(2 * nval)

    return val, err
# -----------------------------
def _plot_distribution(rdf: RDataFrame, var_name : str, cut : str, val : float, err : float) -> None:
    return
    arr_val = rdf.AsNumpy([var_name])[var_name]
    plt.hist(arr_val, histtype='step', bins=30, range=[4500, 6000])

    out_dir = Data.cfg['saving']['plt_dir']
    out_dir = f'{out_dir}/distributions'
    os.makedirs(out_dir, exist_ok=True)

    name = cut
    name = name.replace('>', 'gt')
    name = name.replace('<', 'lt')
    name = name.replace(' ',  '_')
    name = name.replace('=', 'eq')
    name = name.replace('&',  'a')
    name = name.replace('-',  'm')
    name = name.replace('(',  '_')
    name = name.replace(')',  '_')

    std   = numpy.std(arr_val)
    nent  = len(arr_val)
    title = f'{std:.0f}; {nent}'

    plt.title(title)
    plt.axvline(val, color='red')
    plt.axvline(val - err, color='red', linestyle=':')
    plt.axvline(val + err, color='red', linestyle=':')
    plt.savefig(f'{out_dir}/{name}.png')
    plt.close()
# -----------------------------
def _get_resolutions(mat_cut : list[list[str]], plot_name : str) -> list[list[float]]:
    path = f'{Data.cache_dir}/resolutions_{plot_name}.json'
    if os.path.isfile(path):
        log.info(f'Cached values found, loading: {path}')
        with open(path, encoding='utf-8') as ifile:
            mat_res = json.load(ifile)
            return mat_res

    d_rdf = {}
    rdf   = _get_rdf()
    for l_cut in mat_cut:
        for cut in l_cut:
            d_rdf[cut] = rdf.Filter(cut)

    var_name = Data.cfg['target']['variable']
    quantity = Data.cfg['target']['quantity']
    val, err = _get_full_stats(rdf, var_name)

    if quantity == 'RMS':
        d_rms = { cut : rdf.StdDev(var_name) for cut, rdf in d_rdf.items() }
    else:
        raise NotImplementedError(f'Invalid quantity: {quantity}')

    d_frq = { cut : rdf.Count()          for cut, rdf in d_rdf.items() }

    log.info('Evaluating nodes')
    mat_rms = []
    for l_cut in mat_cut:
        l_res = []
        for cut in l_cut:
            rms = d_rms[cut]
            frq = d_frq[cut]
            rdf = d_rdf[cut]

            frq_val = frq.GetValue()
            rms_val = rms.GetValue()

            within_nsigma = val - 3 * err < rms_val < val + 3 * err
            if not within_nsigma:
                _plot_distribution(rdf, var_name, cut, val, err)

            if frq_val == 0:
                log.warning(f'Zero entries at: {cut}')
                l_res.append(0)
            else:
                l_res.append(rms_val)

        mat_rms.append(l_res)

    with open(path, 'w', encoding='utf-8') as ofile:
        json.dump(mat_rms, ofile, indent=4)

    return mat_rms
# -----------------------------
def _get_cuts(l_name : list[str], l_setting : list) -> list[list[str]]:
    l_cutx = _cuts_from_binning(l_name, l_setting, 0)
    l_cuty = _cuts_from_binning(l_name, l_setting, 1)

    l_cut_xy = []
    for cutx in l_cutx:
        l_cut_x = []
        for cuty in l_cuty:
            l_cut_x.append(f'({cutx}) && ({cuty})')

        l_cut_xy.append(l_cut_x)

    return l_cut_xy
# -----------------------------
def _plot(mat_res : list[list[str]], variables : list[str], plot_name : str) -> None:
    [var_x, var_y] = variables
    l_bound_x      = Data.d_bound[var_x]
    l_bound_y      = Data.d_bound[var_y]
    q2bin          = Data.cfg['input']['q2bin']
    sample         = Data.cfg['input']['sample']
    trigger        = Data.cfg['input']['trigger']
    plt_dir        = Data.cfg['saving']['plt_dir']
    figsize        = Data.cfg['general']['size']
    [zmin, zmax]   = Data.cfg['general']['zrange']

    mat_res = numpy.array(mat_res).T
    plt.subplots(figsize=figsize)
    plt.pcolormesh(l_bound_x, l_bound_y, mat_res, cmap="viridis", shading="auto", vmin=zmin, vmax=zmax)
    plt.colorbar()

    plot_path = f'{plt_dir}/{plot_name}_{sample}_{trigger}_{q2bin}.png'
    plot_path = plot_path.replace('*', 'p')

    log.info(f'Saving to: {plot_path}')

    plt.savefig(plot_path)
    plt.close('all')
# -----------------------------
def main():
    '''
    Start here
    '''
    _parse_args()
    _load_config()

    d_plot = Data.cfg['plots']
    for plot_name, d_axis in d_plot.items():
        l_name = list(d_axis.keys())
        l_sett = list(d_axis.values())
        mat_cut= _get_cuts(l_name, l_sett)

        mat_res= _get_resolutions(mat_cut, plot_name)
        _plot(mat_res, l_name, plot_name)
# -----------------------------
if __name__ == '__main__':
    main()
