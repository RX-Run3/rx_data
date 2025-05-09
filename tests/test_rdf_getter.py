'''
Class testing RDFGetter
'''
import os
import matplotlib.pyplot as plt

import pytest
import mplhep
import numpy
from ROOT                    import RDataFrame
from dmu.logging.log_store   import LogStore
from dmu.plotting.plotter_2d import Plotter2D

from rx_selection           import selection as sel
from rx_data.rdf_getter     import RDFGetter, AlreadySetColumns

log=LogStore.add_logger('rx_data:test_rdf_getter')
# ------------------------------------------------
class Data:
    '''
    Class used to share attributes
    '''
    out_dir    = '/tmp/tests/rx_data/rdf_getter'
    low_q2     = '(Jpsi_M * Jpsi_M >        0) && (Jpsi_M * Jpsi_M <  1000000)'
    central_q2 = '(Jpsi_M * Jpsi_M >  1100000) && (Jpsi_M * Jpsi_M <  6000000)'
    jpsi_q2    = '(Jpsi_M * Jpsi_M >  6000000) && (Jpsi_M * Jpsi_M < 12960000)'
    psi2_q2    = '(Jpsi_M * Jpsi_M >  9920000) && (Jpsi_M * Jpsi_M < 16400000)'
    high_q2    = '(Jpsi_M * Jpsi_M > 15500000) && (Jpsi_M * Jpsi_M < 22000000)'

    l_branch_mc = [
            'Jpsi_TRUEM',
            ]

    l_branch_common = [
            'th_l1_l2',
            'th_l1_kp',
            'th_l2_kp',
            'mva.mva_cmb',
            'mva.mva_prc',
            'hop.hop_mass',
            'hop.hop_alpha',
            'cascade.swp_cascade_mass_swp',
            'jpsi_misid.swp_jpsi_misid_mass_swp',
            'Jpsi_Mass',
            'q2',
                      ]

    l_branch_ee = l_branch_common + [
            'brem_track_2.B_M_brem_track_2',
            'L1_TRACK_PT',
            'L1_TRACK_ETA',
            'L1_TRACK_P',
            'L2_TRACK_PT',
            'L2_TRACK_ETA',
            'L2_TRACK_P',
            ]

    l_branch_mm = l_branch_common + []
# ------------------------------------------------
@pytest.fixture(scope='session', autouse=True)
def _initialize():
    LogStore.set_level('rx_data:rdf_getter', 10)
    os.makedirs(Data.out_dir, exist_ok=True)
    plt.style.use(mplhep.style.LHCb2)
    RDFGetter.max_entries = 1000
# ------------------------------------------------
def _check_block(rdf : RDataFrame) -> None:
    arr_block = rdf.AsNumpy(['block'])['block']

    assert numpy.any(arr_block == 0)
    assert numpy.all(arr_block >= 0)
    assert numpy.all(arr_block <= 8)
# ------------------------------------------------
def _check_branches(rdf : RDataFrame, is_ee : bool, is_mc : bool) -> None:
    l_name = [ name.c_str() for name in rdf.GetColumnNames() ]

    l_branch = Data.l_branch_ee if is_ee else Data.l_branch_mm
    if is_mc:
        l_branch += Data.l_branch_mc

    for branch in l_branch:
        if branch in l_name:
            continue

        raise ValueError(f'Branch missing: {branch}')
# ------------------------------------------------
def _print_dotted_branches(rdf : RDataFrame) -> None:
    l_name = [ name.c_str() for name in rdf.GetColumnNames() ]

    for name in l_name:
        if '.' not in name:
            continue

        log.info(name)
# ------------------------------------------------
def _plot_mva_mass(rdf : RDataFrame, test : str) -> None:
    test_dir = f'{Data.out_dir}/{test}'
    os.makedirs(test_dir, exist_ok=True)

    rdf = rdf.Filter(Data.jpsi_q2)

    for cmb in [0.4, 0.6, 0.8, 0.9]:
        rdf      = rdf.Filter(f'mva_cmb > {cmb}')
        arr_mass = rdf.AsNumpy(['B_M'])['B_M']
        plt.hist(arr_mass, bins=50, histtype='step', range=[4800, 5500], label=f'{cmb}; 0.0')

    for prc in [0.5, 0.6]:
        rdf      = rdf.Filter(f'mva_prc > {prc}')
        arr_mass = rdf.AsNumpy(['B_M'])['B_M']
        plt.hist(arr_mass, bins=50, histtype='step', range=[4800, 5500], label=f'{cmb}; {prc}')

    plt.title(test)
    plt.legend()
    plt.savefig(f'{test_dir}/mva_mass.png')
    plt.close()
# ------------------------------------------------
def _plot_block(rdf : RDataFrame, name : str) -> None:
    arr_block = rdf.AsNumpy(['block'])['block']

    os.makedirs(f'{Data.out_dir}/{name}', exist_ok=True)

    plt.hist(arr_block, bins=30)
    plt.savefig(f'{Data.out_dir}/{name}/block.png')
    plt.close()
# ------------------------------------------------
def _plot_q2_track(rdf : RDataFrame, sample : str) -> None:
    test_dir = f'{Data.out_dir}/{sample}'
    os.makedirs(test_dir, exist_ok=True)

    arr_q2_track = rdf.AsNumpy(['q2_track'])['q2_track']
    arr_q2       = rdf.AsNumpy(['q2'      ])['q2'      ]

    plt.hist(arr_q2_track, alpha=0.5      , range=[0, 22_000_000], bins=40, label='$q^2_{track}$')
    plt.hist(arr_q2      , histtype='step', range=[0, 22_000_000], bins=40, label='$q^2$')

    plt.title(sample)
    plt.legend()
    plt.savefig(f'{test_dir}/q2_track.png')
    plt.close()
# ------------------------------------------------
def _plot_sim(rdf : RDataFrame, test : str) -> None:
    test_dir = f'{Data.out_dir}/{test}'
    os.makedirs(test_dir, exist_ok=True)

    arr_mass = rdf.AsNumpy(['Jpsi_TRUEM'])['Jpsi_TRUEM']
    plt.hist(arr_mass, bins=200, range=[3090, 3100], histtype='step', label='CMB')

    plt.title(test)
    plt.legend()
    plt.savefig(f'{test_dir}/jpsi_truem.png')
    plt.close()
# ------------------------------------------------
def _plot_mva(rdf : RDataFrame, test : str) -> None:
    test_dir = f'{Data.out_dir}/{test}'
    os.makedirs(test_dir, exist_ok=True)

    rdf = rdf.Filter(Data.jpsi_q2)

    arr_cmb = rdf.AsNumpy(['mva_cmb'])['mva_cmb']
    arr_prc = rdf.AsNumpy(['mva_prc'])['mva_prc']
    plt.hist(arr_cmb, bins=40, histtype='step', range=[0, 1], label='CMB')
    plt.hist(arr_prc, bins=40, histtype='step', range=[0, 1], label='PRC')

    plt.title(test)
    plt.legend()
    plt.savefig(f'{test_dir}/mva.png')
    plt.close()
# ------------------------------------------------
def _plot_hop(rdf : RDataFrame, test : str) -> None:
    test_dir = f'{Data.out_dir}/{test}'
    os.makedirs(test_dir, exist_ok=True)

    rdf = rdf.Filter(Data.jpsi_q2)

    arr_org = rdf.AsNumpy(['B_M' ])['B_M' ]
    arr_hop = rdf.AsNumpy(['hop_mass'])['hop_mass']
    plt.hist(arr_org, bins=80, histtype='step', range=[3000, 7000], label='Original')
    plt.hist(arr_hop, bins=80, histtype='step', range=[3000, 7000], label='HOP')
    plt.title(test)
    plt.legend()
    plt.savefig(f'{test_dir}/hop_mass.png')
    plt.close()

    arr_aph = rdf.AsNumpy(['hop_alpha'])['hop_alpha']
    plt.hist(arr_aph, bins=40, histtype='step', range=[0, 5])
    plt.title(test)
    plt.savefig(f'{test_dir}/hop_alpha.png')
    plt.close()
# ------------------------------------------------
def _apply_selection(rdf : RDataFrame, trigger : str, sample : str, override : dict[str,str] = None) -> RDataFrame:
    d_sel = sel.selection(project='RK', trigger=trigger, q2bin='jpsi', process=sample)
    if override is not None:
        d_sel.update(override)

    for cut_name, cut_expr in d_sel.items():
        if cut_name in ['mass', 'q2']:
            continue
        rdf = rdf.Filter(cut_expr, cut_name)

    return rdf
# ------------------------------------------------
def _plot_brem_track_2(rdf : RDataFrame, test : str, tree : str) -> None:
    test_dir = f'{Data.out_dir}/{test}/{tree}'
    os.makedirs(test_dir, exist_ok=True)

    d_var= {
            'B_M'             : [4200,  6000],
            'Jpsi_M'          : [2500,  3300],
            'L1_PT'           : [   0, 10000],
            'L2_PT'           : [   0, 10000],
            'L1_HASBREMADDED' : [0, 2],
            'L2_HASBREMADDED' : [0, 2],
            }

    kind = 'brem_track_2'
    for var, rng in d_var.items():
        name = f'{kind}.{var}_{kind}'
        arr_org = rdf.AsNumpy([var ])[var ]
        arr_cor = rdf.AsNumpy([name])[name]

        plt.hist(arr_org, bins=50, alpha=0.5      , range=rng, label='Original' , color='gray')
        plt.hist(arr_cor, bins=50, histtype='step', range=rng, label='Corrected', color='blue')

        plt.title(f'{var}; {test}')
        plt.legend()
        plt.savefig(f'{test_dir}/{var}.png')
        plt.close()
# ------------------------------------------------
def _plot_ext(rdf : RDataFrame, sample : str) -> None:
    cfg = {
            'saving'   : {'plt_dir' : f'{Data.out_dir}/ext'},
            'general'  : {'size' : [20, 10]},
            'plots_2d' :
            [['L1_PID_E', 'L2_PID_E', 'weight', f'PIDe_wgt_{sample}', True],
             ['L1_PID_E', 'L2_PID_E',     None, f'PIDe_raw_{sample}', True]],
            'axes' :
            {
                'L1_PID_E' : {'binning' : [-5, 13, 60], 'label': r'$\Delta LL(e^+)$'},
                'L2_PID_E' : {'binning' : [-5, 13, 60], 'label': r'$\Delta LL(e^-)$'},
                },
            }

    ptr=Plotter2D(rdf=rdf, cfg=cfg)
    ptr.run()
# ------------------------------------------------
def _check_ext(rdf : RDataFrame) -> None:
    rdf_ana = rdf.Filter('L1_PID_E > 1 && L2_PID_E > 1')
    rdf_mis = rdf.Filter('L1_PID_E < 1 || L2_PID_E < 1')

    count_ana = rdf_ana.Count().GetValue()
    count_mis = rdf_mis.Count().GetValue()

    log.info(f'Analysis: {count_ana}')
    log.info(f'MisID   : {count_mis}')
# ------------------------------------------------
@pytest.mark.parametrize('sample' , ['DATA_24_MagDown_24c2'])
@pytest.mark.parametrize('trigger', ['Hlt2RD_BuToKpEE_MVA', 'Hlt2RD_BuToKpMuMu_MVA' ])
def test_data(sample : str, trigger : str):
    '''
    Test of getter class in data
    '''
    gtr = RDFGetter(sample=sample, trigger=trigger)
    rdf = gtr.get_rdf()
    rdf = _apply_selection(rdf=rdf, trigger=trigger, sample=sample)
    rep = rdf.Report()
    rep.Print()

    _check_branches(rdf, is_ee = 'MuMu' not in trigger, is_mc = False)

    sample = sample.replace('*', 'p')

    _plot_mva_mass(rdf, sample)
    _plot_mva(rdf, sample)
    _plot_hop(rdf, sample)
# ------------------------------------------------
@pytest.mark.parametrize('sample', ['Bu_JpsiK_ee_eq_DPC'])
def test_mc(sample : str):
    '''
    Test of getter class in mc
    '''

    gtr = RDFGetter(sample=sample, trigger='Hlt2RD_BuToKpEE_MVA')
    rdf = gtr.get_rdf()

    _check_branches(rdf, is_ee=True, is_mc=True)

    _plot_mva_mass(rdf, f'test_mc/{sample}')
    _plot_mva(rdf     , f'test_mc/{sample}')
    _plot_hop(rdf     , f'test_mc/{sample}')
    _plot_sim(rdf     , f'test_mc/{sample}')
# ------------------------------------------------
@pytest.mark.parametrize('sample' , ['DATA_24_MagDown_24c2', 'Bu_JpsiK_ee_eq_DPC', 'Bu_psi2SK_ee_eq_DPC', 'Bu_JpsiX_ee_eq_JpsiInAcc'])
def test_q2_track_electron(sample : str):
    '''
    Checks the distributions of q2_track vs normal q2
    '''
    trigger = 'Hlt2RD_BuToKpEE_MVA'

    gtr = RDFGetter(sample=sample, trigger=trigger)
    rdf = gtr.get_rdf()
    rdf = _apply_selection(rdf=rdf, trigger=trigger, sample=sample)
    rep = rdf.Report()
    rep.Print()

    is_mc = not sample.startswith('DATA_24_')
    _check_branches(rdf, is_ee=True, is_mc = is_mc)

    sample = sample.replace('*', 'p')

    _plot_q2_track(rdf, sample)
# ------------------------------------------------
@pytest.mark.parametrize('sample' , ['DATA_24_MagDown_24c2', 'Bu_Kmumu_eq_btosllball05_DPC'])
def test_q2_track_muon(sample : str):
    '''
    Checks the distributions of q2_track vs normal q2
    '''
    trigger = 'Hlt2RD_BuToKpMuMu_MVA'

    gtr = RDFGetter(sample=sample, trigger=trigger)
    rdf = gtr.get_rdf()
    rdf = _apply_selection(rdf=rdf, trigger=trigger, sample=sample)
    rep = rdf.Report()
    rep.Print()

    is_mc = not sample.startswith('DATA_24_')
    _check_branches(rdf, is_ee=False, is_mc=is_mc)

    sample     = sample.replace('*', 'p')
    identifier = f'{trigger}_{sample}'

    _plot_q2_track(rdf, identifier)
# ------------------------------------------------
@pytest.mark.parametrize('sample' , ['DATA_24_MagDown_24c2', 'Bu_JpsiK_ee_eq_DPC'])
@pytest.mark.parametrize('trigger', ['Hlt2RD_BuToKpEE_MVA'])
def test_brem_track_2(sample : str, trigger : str):
    '''
    Test brem_track_2 correction
    '''
    gtr = RDFGetter(sample=sample, trigger=trigger)
    rdf = gtr.get_rdf()
    rdf = _apply_selection(rdf=rdf, trigger=trigger, override = {'mass' : 'B_const_mass_M > 5160'}, sample=sample)
    rep = rdf.Report()
    rep.Print()

    is_mc = not sample.startswith('DATA_24_')
    _check_branches(rdf, is_ee=True, is_mc=is_mc)

    sample = sample.replace('*', 'p')
    _plot_brem_track_2(rdf, sample, 'brem_track_2')
# ------------------------------------------------
@pytest.mark.parametrize('sample', ['Bu_JpsiK_ee_eq_DPC', 'DATA_24_MagDown_24c2'])
def test_check_vars(sample : str):
    '''
    Checks that variables from:

    - Friend trees
    - Added branches, e.g. L*_TRACK_P/ETA, etc

    Can be accessed
    '''
    gtr = RDFGetter(sample=sample, trigger='Hlt2RD_BuToKpEE_MVA')
    rdf = gtr.get_rdf()

    is_mc = not sample.startswith('DATA_24_')
    _check_branches(rdf, is_ee=True, is_mc=is_mc)

    _print_dotted_branches(rdf)
# ------------------------------------------------
@pytest.mark.parametrize('sample', ['Bu_JpsiK_ee_eq_DPC'])
def test_mcdecaytree(sample : str):
    '''
    Builds dataframe from MCDecayTree
    '''
    gtr = RDFGetter(sample=sample, trigger='Hlt2RD_BuToKpEE_MVA', tree='MCDecayTree')
    rdf = gtr.get_rdf()

    nentries = rdf.Count().GetValue()

    log.info(f'Found {nentries} entries')

    assert nentries > 0
# ------------------------------------------------
@pytest.mark.parametrize('period'  ,['24c1','24c2','24c3','24c4'])
@pytest.mark.parametrize('polarity',['MagUp', 'MagDown'])
def test_ext_trigger(period : str, polarity : str):
    '''
    Test of getter class for combination of analysis and misID trigger
    '''
    sample=f'DATA_24_{polarity}_{period}'
    trigger='Hlt2RD_BuToKpEE_MVA_ext'

    RDFGetter.max_entries = -1
    gtr = RDFGetter(sample=sample, trigger=trigger)
    rdf = gtr.get_rdf()

    _check_ext(rdf)
    _plot_ext(rdf, sample=sample)
# ------------------------------------------------
def test_define_custom_branches():
    '''
    Tests defining of new custom columns
    '''
    d_def = {
            'xbrem' : 'int(L1_HASBREMADDED_brem_track_2) + int(L2_HASBREMADDED_brem_track_2)',
            'xmva'  : 'mva_cmb + mva_prc',
            }

    RDFGetter.set_custom_columns(d_def = d_def)
    with pytest.raises(AlreadySetColumns):
        RDFGetter.set_custom_columns(d_def = d_def)

    obj = RDFGetter(trigger='Hlt2RD_BuToKpEE_MVA', sample='DATA_24_MagDown_24c2')
    rdf = obj.get_rdf()

    l_col = [ col.c_str() for col in rdf.GetColumnNames() ]

    assert 'xbrem' in l_col
    assert 'xmva'  in l_col
# ------------------------------------------------
@pytest.mark.parametrize('sample' , ['DATA*'])
@pytest.mark.parametrize('trigger', ['Hlt2RD_BuToKpEE_MVA', 'Hlt2RD_BuToKpMuMu_MVA' ])
def test_block(sample : str, trigger : str):
    '''
    Test of getter class with check for block assignment
    '''
    RDFGetter.max_entries = -1
    gtr = RDFGetter(sample=sample, trigger=trigger)
    rdf = gtr.get_rdf()
    rdf = _apply_selection(rdf=rdf, trigger=trigger, sample=sample)
    rep = rdf.Report()
    rep.Print()

    _check_block(rdf)

    sample = sample.replace('*', 'p')
    name   = f'block/{sample}_{trigger}'

    _plot_block(rdf=rdf, name=name)
    RDFGetter.max_entries = 1000
# ------------------------------------------------
