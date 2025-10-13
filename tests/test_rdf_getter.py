'''
Class testing RDFGetter
'''
import os
import glob
import math
from typing import cast

import matplotlib.pyplot as plt
import pandas            as pnd
import pytest
import mplhep
import numpy
from ROOT                    import RDataFrame, GetThreadPoolSize, RDF # type: ignore
from dmu.logging.log_store   import LogStore
from dmu.plotting.plotter_2d import Plotter2D
from dmu.generic             import utilities as gut
from dmu.rdataframe          import utilities as ut

from rx_selection           import selection as sel
from rx_data                import collector as col
from rx_data.rdf_getter     import RDFGetter

# TODO: Need test for default_skip manager
log=LogStore.add_logger('rx_data:test_rdf_getter')
# ------------------------------------------------
class Data:
    '''
    Class used to share attributes
    '''
    # ----------------------
    out_dir    : str 
    low_q2     = '(Jpsi_M * Jpsi_M >        0) && (Jpsi_M * Jpsi_M <  1000000)'
    central_q2 = '(Jpsi_M * Jpsi_M >  1100000) && (Jpsi_M * Jpsi_M <  6000000)'
    jpsi_q2    = '(Jpsi_M * Jpsi_M >  6000000) && (Jpsi_M * Jpsi_M < 12960000)'
    psi2_q2    = '(Jpsi_M * Jpsi_M >  9920000) && (Jpsi_M * Jpsi_M < 16400000)'
    high_q2    = '(Jpsi_M * Jpsi_M > 15500000) && (Jpsi_M * Jpsi_M < 22000000)'

    l_branch_mc = [
        'Jpsi_TRUEM',
        'B_TRUEM']

    l_branch_friends = [
        'mva_cmb',
        'mva_prc',
        'hop_mass',
        'hop_alpha',
        'swp_cascade_mass_swp',
        'swp_jpsi_misid_mass_swp',
        ]

    l_branch_common = [
        'th_l1_l2',
        'th_l1_kp',
        'th_l2_kp',
        'q2']

    l_branch_ee = l_branch_common + [
        'L1_TRACK_PT',
        'L1_TRACK_ETA',
        'L1_TRACK_P',
        'L2_TRACK_PT',
        'L2_TRACK_ETA',
        'L2_TRACK_P']

    l_brem_track_2 = [
        'B_Mass_smr',
        'Jpsi_Mass_smr',
        'B_Mass',
        'Jpsi_Mass',
        'q2_smr',
        'B_M_brem_track_2']

    l_branch_mm = l_branch_common + ['B_Mass', 'Jpsi_Mass']
    l_q2bin     = ['low', 'cen_low', 'central', 'cen_high', 'psi2', 'high']
# --------------------------
@pytest.fixture(scope='session', autouse=True)
def initialize(out_dir):
    '''
    This will run before any test
    '''
    LogStore.set_level('rx_data:rdf_getter', 10)
    plt.style.use(mplhep.style.LHCb2)

    Data.out_dir = f'{out_dir}/rdf_getter'
    os.makedirs(Data.out_dir, exist_ok=True)
# ------------------------------------------------
def _check_truem_columns(rdf : RDF.RNode):
    l_name = [ name for name in rdf.GetColumnNames() if name.endswith('_TRUEM') ]
    d_data = rdf.AsNumpy(l_name)
    df     = pnd.DataFrame(d_data)
    nnan   = df.isna().sum().sum()
    ntot   = len(df)

    if nnan > 0:
        raise ValueError(f'Found {nnan}/{ntot} NaNs in dataframe')
# ------------------------------------------------
def _check_block(rdf : RDF.RNode) -> None:
    arr_block = rdf.AsNumpy(['block'])['block']

    assert numpy.all(arr_block >= 0)
    assert numpy.all(arr_block <= 8)
# ----------------------
def _name_from_raw_name(name : str) -> str:
    '''
    Parameters
    -------------
    name: Branch name as taken from dataframe

    Returns
    -------------
    Branch name as needed for check
    '''
    if '.' not in name:
        return name

    l_name = name.split('.')

    return l_name[-1]
# ------------------------------------------------
def _check_branches(
    rdf          : RDF.RNode,
    is_ee        : bool,
    is_mc        : bool,
    friends      : bool = True,
    brem_track_2 : bool = True) -> None:

    l_name = [ _name_from_raw_name(name=name) for name in rdf.GetColumnNames() ]

    if brem_track_2:
        l_branch_ee = Data.l_brem_track_2 + Data.l_branch_ee
    else:
        l_branch_ee = Data.l_branch_ee

    l_branch = l_branch_ee if is_ee else Data.l_branch_mm
    if is_mc:
        l_branch = Data.l_branch_mc + l_branch

    if friends:
        l_branch = l_branch + Data.l_branch_friends

    for branch in l_branch:
        if branch in l_name:
            continue

        raise ValueError(f'Branch missing: {branch}')
# ------------------------------------------------
def _print_dotted_branches(rdf : RDF.RNode) -> None:
    l_name = [ name for name in rdf.GetColumnNames() ]

    for name in l_name:
        if '.' not in name:
            continue

        log.info(name)
# ------------------------------------------------
def _plot_mva_mass(rdf : RDF.RNode, test : str) -> None:
    test_dir = f'{Data.out_dir}/{test}'
    os.makedirs(test_dir, exist_ok=True)

    rdf = rdf.Filter(Data.jpsi_q2)

    cmb = 0.0
    for cmb in [0.4, 0.6, 0.8, 0.9]:
        rdf      = rdf.Filter(f'mva_cmb > {cmb}')
        arr_mass = rdf.AsNumpy(['B_M'])['B_M']
        plt.hist(arr_mass, bins=50, histtype='step', range=(4800, 5500), label=f'{cmb}; 0.0')

    for prc in [0.5, 0.6]:
        rdf      = rdf.Filter(f'mva_prc > {prc}')
        arr_mass = rdf.AsNumpy(['B_M'])['B_M']
        plt.hist(arr_mass, bins=50, histtype='step', range=(4800, 5500), label=f'{cmb}; {prc}')

    plt.title(test)
    plt.legend()
    plt.savefig(f'{test_dir}/mva_mass.png')
    plt.close()
# ------------------------------------------------
def _plot_block(rdf : RDF.RNode, name : str) -> None:
    arr_block = rdf.AsNumpy(['block'])['block']

    os.makedirs(f'{Data.out_dir}/{name}', exist_ok=True)

    plt.hist(arr_block, bins=30)
    plt.savefig(f'{Data.out_dir}/{name}/block.png')
    plt.close()
# ------------------------------------------------
def _plot_bmass(
    rdf         : RDF.RNode,
    is_electron : bool,
    brem_track_2: bool,
    test_name   : str) -> None:
    test_dir = f'{Data.out_dir}/{test_name}'
    os.makedirs(test_dir, exist_ok=True)

    minx = 4500
    maxx = 6000
    if is_electron and brem_track_2:
        masses = ['B_Mass_smr', 'B_M']
    else:
        masses = ['B_M']

    data = rdf.AsNumpy(masses)
    df   = pnd.DataFrame(data)

    df.plot.hist(range=[minx, maxx], bins=100, histtype='step')

    plt.title(test_name)
    plt.legend()
    plt.savefig(f'{test_dir}/bmass.png')
    plt.close()
# ------------------------------------------------
def _plot_q2_track(rdf : RDF.RNode, sample : str) -> None:
    test_dir = f'{Data.out_dir}/{sample}'
    os.makedirs(test_dir, exist_ok=True)

    arr_q2_track = rdf.AsNumpy(['q2_track'])['q2_track']
    arr_q2       = rdf.AsNumpy(['q2'      ])['q2'      ]

    plt.hist(arr_q2_track, alpha=0.5      , range=(0, 22_000_000), bins=40, label='$q^2_{track}$')
    plt.hist(arr_q2      , histtype='step', range=(0, 22_000_000), bins=40, label='$q^2$')

    plt.title(sample)
    plt.legend()
    plt.savefig(f'{test_dir}/q2_track.png')
    plt.close()
# ------------------------------------------------
def _plot_sim(rdf : RDF.RNode, test : str, particle : str) -> None:
    test_dir = f'{Data.out_dir}/{test}'
    os.makedirs(test_dir, exist_ok=True)

    arr_mass = rdf.AsNumpy([f'{particle}_TRUEM'])[f'{particle}_TRUEM']

    if   particle == 'B':
        plt.hist(arr_mass, bins=200, range=(5000, 5300), histtype='step', label='True')
        plt.axvline(x=5279.3, c='red', ls=':', label=r'$B^+$')
    elif particle == 'Jpsi' and 'Jpsi'     in test: # This will do the resonant sample
        plt.hist(arr_mass, bins=200, range=(3090, 3100), histtype='step', label='True')
        plt.axvline(x=3096.9, c='red', ls=':', label=r'$J/\psi$')
    elif particle == 'Jpsi' and 'Jpsi' not in test: # This will do the rare one
        plt.hist(arr_mass, bins=200, range=(   0, 4500), histtype='step', label='True')
    else:
        raise ValueError(f'Invalid test/particle: {test}/{particle}')

    plt.title(test)
    plt.legend()
    plt.savefig(f'{test_dir}/{particle}_truem.png')
    plt.close()
# ------------------------------------------------
def _plot_mva(rdf : RDF.RNode, test : str) -> None:
    test_dir = f'{Data.out_dir}/{test}'
    os.makedirs(test_dir, exist_ok=True)

    rdf = rdf.Filter(Data.jpsi_q2)

    arr_cmb = rdf.AsNumpy(['mva_cmb'])['mva_cmb']
    arr_prc = rdf.AsNumpy(['mva_prc'])['mva_prc']
    plt.hist(arr_cmb, bins=40, histtype='step', range=(-1.1, 1.0), label='CMB')
    plt.hist(arr_prc, bins=40, histtype='step', range=(-1.1, 1.0), label='PRC')

    plt.title(test)
    plt.legend()
    plt.savefig(f'{test_dir}/mva.png')
    plt.close()
# ------------------------------------------------
def _plot_hop(rdf : RDF.RNode, test : str) -> None:
    test_dir = f'{Data.out_dir}/{test}'
    os.makedirs(test_dir, exist_ok=True)

    rdf = rdf.Filter(Data.jpsi_q2)

    arr_org = rdf.AsNumpy(['B_M' ])['B_M' ]
    arr_hop = rdf.AsNumpy(['hop_mass'])['hop_mass']
    plt.hist(arr_org, bins=80, histtype='step', range=(3000, 7000), label='Original')
    plt.hist(arr_hop, bins=80, histtype='step', range=(3000, 7000), label='HOP')
    plt.title(test)
    plt.legend()
    plt.savefig(f'{test_dir}/hop_mass.png')
    plt.close()

    arr_aph = rdf.AsNumpy(['hop_alpha'])['hop_alpha']
    plt.hist(arr_aph, bins=40, histtype='step', range=(0, 5))
    plt.title(test)
    plt.savefig(f'{test_dir}/hop_alpha.png')
    plt.close()
# ------------------------------------------------
def _apply_selection(
    rdf      : RDF.RNode,
    trigger  : str,
    sample   : str,
    override : None|dict[str,str] = None) -> RDF.RNode:
    '''
    Apply full selection but q2 and mass
    '''
    d_sel = sel.selection(trigger=trigger, q2bin='jpsi', process=sample)
    if override is not None:
        d_sel.update(override)

    for cut_name, cut_expr in d_sel.items():
        if cut_name in ['mass', 'q2']:
            continue
        rdf = rdf.Filter(cut_expr, cut_name)

    return rdf
# ------------------------------------------------
def _plot_brem_track_2(rdf : RDF.RNode, test : str, tree : str) -> None:
    test_dir = f'{Data.out_dir}/{test}/{tree}'
    os.makedirs(test_dir, exist_ok=True)

    d_var= {
        'B_M'             : (4200,  6000),
        'Jpsi_M'          : (2500,  3300),
        'L1_PT'           : (   0, 10000),
        'L2_PT'           : (   0, 10000),
        'L1_HASBREMADDED' : (   0,     2),
        'L2_HASBREMADDED' : (   0,     2),
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
def _plot_mc_qsq(rdf : RDF.RNode, test : str, sample : str) -> None:
    test_dir = f'{Data.out_dir}/{test}'
    os.makedirs(test_dir, exist_ok=True)

    l_qsq= ['q2_true', 'q2_smr', 'q2_track', 'q2_dtf']

    data = rdf.AsNumpy(l_qsq)
    df   = pnd.DataFrame(data)
    df   = df / 1e6

    df['q2_true' ].plot.hist(bins=60, range=[0, 25], alpha   =   0.3, label='True')
    df['q2_smr'  ].plot.hist(bins=60, range=[0, 25], histtype='step', label='Smeared')
    df['q2_track'].plot.hist(bins=60, range=[0, 25], histtype='step', label='Track')
    df['q2_dtf'  ].plot.hist(bins=60, range=[0, 25], histtype='step', label='DTF')

    plt.title(sample)
    plt.legend()
    plt.savefig(f'{test_dir}/q2.png')
    plt.close()
# ------------------------------------------------
def _plot_ext(rdf : RDF.RNode, sample : str) -> None:
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
def _check_ext(rdf : RDF.RNode) -> None:
    rdf_ana = rdf.Filter('L1_PID_E > 1 && L2_PID_E > 1')
    rdf_mis = rdf.Filter('L1_PID_E < 1 || L2_PID_E < 1')

    count_ana = rdf_ana.Count().GetValue()
    count_mis = rdf_mis.Count().GetValue()

    log.info(f'Analysis: {count_ana}')
    log.info(f'MisID   : {count_mis}')
# ------------------------------------------------
def _check_mva_scores(
        rdf : RDF.RNode,
        ) -> None:
    '''
    Checks that the event number and run number are aligned between
    main tree and MVA tree
    '''
    l_branch = [
            'mva.EVENTNUMBER',
            'mva.RUNNUMBER',
            'EVENTNUMBER',
            'RUNNUMBER']

    data = rdf.AsNumpy(l_branch)

    ev1 = data['mva.EVENTNUMBER']
    ev2 = data[    'EVENTNUMBER']

    rn1 = data['mva.RUNNUMBER'  ]
    rn2 = data[    'RUNNUMBER'  ]

    assert numpy.array_equal(ev1, ev2)
    assert numpy.array_equal(rn1, rn2)
# ------------------------------------------------
def _check_mcdt(rdf : RDF.RNode, name : str) -> None:
    '''
    Parameters
    -------------
    rdf: ROOT DataFrame with MCDecayTree
    name: Name of test, for outputs

    Returns
    -------------
    None
    '''
    arr_q2 = rdf.AsNumpy(['q2'])['q2']
    arr_q2 = arr_q2 / 1000_000

    test_dir = f'{Data.out_dir}/{name}'
    os.makedirs(test_dir, exist_ok=True)

    plt.hist(arr_q2, bins=60, range=(0, 22), histtype='step')
    plt.savefig(f'{test_dir}/q2.png')
    plt.close()
# ------------------------------------------------
def _run_default_checks(
    rdf          : RDF.RNode,
    test_name    : str,
    trigger      : str,
    sample       : str,
    friends      : bool = True,
    brem_track_2 : bool = True) -> None:

    _check_branches(
        rdf,
        is_ee        = 'MuMu' not in trigger,
        is_mc        = False,
        friends      = friends,
        brem_track_2 = brem_track_2)

    sample = sample.replace('*', 'p')

    _plot_bmass(
        brem_track_2 = brem_track_2,
        rdf          = rdf,
        is_electron  = 'MuMu' not in trigger,
        test_name    = f'{test_name}_{sample}')

    if not friends: # Not friends no checks below
        return

    _check_mva_scores(rdf=rdf)
    _plot_mva_mass(rdf, f'{test_name}_{sample}')
    _plot_mva(rdf     , f'{test_name}_{sample}')
    _plot_hop(rdf     , f'{test_name}_{sample}')
# ------------------------------------------------
@pytest.mark.parametrize('per_file', [True, False])
@pytest.mark.parametrize('trigger' , ['Hlt2RD_BuToKpEE_MVA', 'Hlt2RD_B0ToKpPimEE_MVA'])
def test_guid(trigger : str, per_file : bool):
    '''
    Tests retrieval of unique identifier for underlying data
    '''
    sam1= 'Bd_Kstee_eq_btosllball05_DPC'
    sam2= 'Bu_K2stee_Kpipi_eq_mK1430_DPC'

    with pytest.raises(ValueError):
        gtr11= RDFGetter(sample=sam1, trigger=trigger)
        gtr11.get_uid()
        gtr11.get_rdf(per_file=per_file)

    gtr11= RDFGetter(sample=sam1, trigger=trigger)
    gtr11.get_rdf(per_file=per_file)
    uid11= gtr11.get_uid()

    gtr12= RDFGetter(sample=sam1, trigger=trigger)
    gtr12.get_rdf(per_file=per_file)
    uid12= gtr12.get_uid()

    gtr22= RDFGetter(sample=sam2, trigger=trigger)
    gtr22.get_rdf(per_file=per_file)
    uid22= gtr22.get_uid()

    # Filtering done here should change the sample's UID
    with RDFGetter.max_entries(value = 100):
        gtr23= RDFGetter(sample=sam2, trigger=trigger)
        gtr23.get_rdf(per_file=per_file)
        uid23= gtr23.get_uid()

    assert uid11 == uid12
    assert uid11 != uid22
    assert uid22 != uid23
# ------------------------------------------------
@pytest.mark.parametrize('sample'   , ['Bd_Kstee_eq_btosllball05_DPC'])
@pytest.mark.parametrize('trigger'  , ['Hlt2RD_BuToKpEE_MVA', 'Hlt2RD_B0ToKpPimEE_MVA'])
@pytest.mark.parametrize('requested', [1_000, 10_000, 20_000])
def test_max_entries(sample : str, requested : int, trigger : str):
    '''
    Check that one can filter randomly entries in dataframe
    '''
    with RDFGetter.max_entries(value=requested):
        gtr = RDFGetter(sample=sample, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    nentries = rdf.Count().GetValue()

    log.info(f'Found {nentries} entries')

    assert math.isclose(nentries, requested, rel_tol=0.1)
# ------------------------------------------------
@pytest.mark.parametrize('kind'   , ['data', 'mc'])
@pytest.mark.parametrize('trigger', ['Hlt2RD_BuToKpEE_MVA', 'Hlt2RD_B0ToKpPimEE_MVA'])
def test_per_file(kind : str, trigger : str):
    '''
    Test of per_file flag set to True
    '''
    if   kind == 'data':
        sample = 'DATA_24_MagDown_24c2'
    elif kind == 'mc' and 'EE'   in trigger:
        sample = 'Bd_Kstee_eq_btosllball05_DPC'
    elif kind == 'mc' and 'MuMu' in trigger:
        sample = 'Bd_Kstmumu_eq_btosllball05_DPC'
    else:
        raise ValueError(f'Invalid kind/trigger: {kind}/{trigger}')

    gtr   = RDFGetter(sample=sample, trigger=trigger)
    d_rdf = gtr.get_rdf(per_file=True)

    for name, rdf in d_rdf.items():
        name = hash(name)
        name = abs(name)
        name = str(name)
        name = name[:10]

        # TODO: Remove when we have friend trees for RKst
        if 'B0ToKpPim' in trigger:
            continue

        _check_branches(rdf, is_ee = 'MuMu' not in trigger, is_mc = False)

        sample = sample.replace('*', 'p')

        _plot_mva_mass(rdf, f'{name}_{sample}')
        _plot_mva(rdf     , f'{name}_{sample}')
        _plot_hop(rdf     , f'{name}_{sample}')
# ------------------------------------------------
@pytest.mark.parametrize('kind'   , ['data', 'mc'])
@pytest.mark.parametrize('trigger', ['Hlt2RD_BuToKpEE_MVA', 'Hlt2RD_B0ToKpPimEE_MVA'])
def test_electron(kind : str, trigger : str):
    '''
    Tests for electron samples
    '''

    if   kind == 'data':
        sample = 'DATA_24_MagDown_24c2'
    elif kind == 'mc':
        sample = 'Bd_Kstee_eq_btosllball05_DPC'
    else:
        raise ValueError(f'Invalid kind/trigger: {kind}/{trigger}')

    with RDFGetter.max_entries(50_000):
        gtr = RDFGetter(sample=sample, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    if 'B0ToKpPim' in trigger:
        return

    _run_default_checks(
        rdf      =rdf,
        test_name='electron',
        trigger  =trigger,
        sample   =sample)
# ------------------------------------------------
@pytest.mark.parametrize(
    'sample' , [
    'DATA_24_MagDown_24c2',
    'DATA_24_MagDown_24c3',
    'DATA_24_MagDown_24c4',
    'DATA_24_MagUp_24c2',
    'DATA_24_MagUp_24c3',
    'DATA_24_MagUp_24c4'])
@pytest.mark.parametrize('trigger', 
    ['Hlt2RD_BuToKpEE_MVA', 
     'Hlt2RD_BuToKpMuMu_MVA',
     'Hlt2RD_B0ToKpPimEE_MVA',
     'Hlt2RD_B0ToKpPimMuMu_MVA'])
def test_data(sample : str, trigger : str):
    '''
    Test of getter class in data
    '''
    gtr = RDFGetter(sample=sample, trigger=trigger)
    rdf = gtr.get_rdf(per_file=False)

    rdf = _apply_selection(rdf=rdf, trigger=trigger, sample=sample)
    rep = rdf.Report()
    rep.Print()

    if 'B0ToKpPim' in trigger:
        return

    _run_default_checks(
        rdf      =rdf,
        sample   =sample,
        trigger  =trigger,
        test_name=f'data_{sample}_{trigger}')
# ------------------------------------------------
@pytest.mark.parametrize('sample', ['Bu_Kee_eq_btosllball05_DPC'])
@pytest.mark.parametrize('trigger', ['Hlt2RD_BuToKpEE_MVA', 'Hlt2RD_B0ToKpPimEE_MVA'])
def test_mc(sample : str, trigger : str):
    '''
    Test of getter class in mc
    '''
    with RDFGetter.max_entries(value=-1):
        gtr = RDFGetter(sample=sample, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    _plot_sim(rdf     , f'test_mc/{sample}', particle=   'B')
    _plot_sim(rdf     , f'test_mc/{sample}', particle='Jpsi')


    if 'B0ToKpPim' in trigger:
        return

    _print_dotted_branches(rdf)
    _check_branches(rdf, is_ee=True, is_mc=True)

    _plot_mc_qsq(rdf, f'test_mc/{sample}', sample)
    _plot_mva_mass(rdf, f'test_mc/{sample}')
    _plot_mva(rdf     , f'test_mc/{sample}')
    _plot_hop(rdf     , f'test_mc/{sample}')
# ------------------------------------------------
@pytest.mark.parametrize('sample' , ['DATA_24_MagDown_24c2', 'Bd_Kstee_eq_btosllball05_DPC'])
@pytest.mark.parametrize('trigger', ['Hlt2RD_BuToKpEE_MVA', 'Hlt2RD_B0ToKpPimEE_MVA'])
def test_q2_track_electron(sample : str, trigger : str):
    '''
    Checks the distributions of q2_track vs normal q2
    '''

    gtr = RDFGetter(sample=sample, trigger=trigger)
    rdf = gtr.get_rdf(per_file=False)
    rdf = _apply_selection(rdf=rdf, trigger=trigger, sample=sample)
    rep = rdf.Report()
    rep.Print()

    sample = sample.replace('*', 'p')
    _plot_q2_track(rdf, sample)

    if 'B0ToKpPim' in trigger:
        return

    is_mc = not sample.startswith('DATA_24_')
    _check_branches(rdf, is_ee=True, is_mc = is_mc)
# ------------------------------------------------
@pytest.mark.parametrize('sample' , ['DATA_24_MagDown_24c2', 'Bd_Kstmumu_eq_btosllball05_DPC'])
@pytest.mark.parametrize('trigger', ['Hlt2RD_BuToKpMuMu_MVA', 'Hlt2RD_B0ToKpPimMuMu_MVA'])
def test_q2_track_muon(sample : str, trigger : str):
    '''
    Checks the distributions of q2_track vs normal q2
    '''
    gtr = RDFGetter(sample=sample, trigger=trigger)
    rdf = gtr.get_rdf(per_file=False)
    rdf = _apply_selection(rdf=rdf, trigger=trigger, sample=sample)
    rep = rdf.Report()
    rep.Print()

    sample     = sample.replace('*', 'p')
    identifier = f'{trigger}_{sample}'

    _plot_q2_track(rdf, identifier)

    if 'B0ToKpPim' in trigger:
        return

    is_mc = not sample.startswith('DATA_24_')
    _check_branches(rdf, is_ee=False, is_mc=is_mc)
# ------------------------------------------------
@pytest.mark.parametrize('sample' , ['DATA_24_MagDown_24c2', 'Bu_JpsiK_ee_eq_DPC'])
@pytest.mark.parametrize('trigger', ['Hlt2RD_BuToKpEE_MVA'])
def test_brem_track_2(sample : str, trigger : str):
    '''
    Test brem_track_2 correction
    '''
    gtr = RDFGetter(sample=sample, trigger=trigger)
    rdf = gtr.get_rdf(per_file=False)
    rdf = _apply_selection(rdf=rdf, trigger=trigger, override = {'mass' : 'B_const_mass_M > 5160'}, sample=sample)
    rep = rdf.Report()
    rep.Print()

    is_mc = not sample.startswith('DATA_24_')
    _check_branches(rdf, is_ee=True, is_mc=is_mc)

    sample = sample.replace('*', 'p')
    _plot_brem_track_2(rdf, sample, 'brem_track_2')
# ------------------------------------------------
@pytest.mark.parametrize('sample', ['Bd_Kstee_eq_btosllball05_DPC', 'DATA_24_MagDown_24c2'])
@pytest.mark.parametrize('trigger', ['Hlt2RD_BuToKpEE_MVA', 'Hlt2RD_B0ToKpPimEE_MVA'])
def test_check_vars(sample : str, trigger : str):
    '''
    Checks that variables from:

    - Friend trees
    - Added branches, e.g. L*_TRACK_P/ETA, etc

    Can be accessed
    '''
    gtr = RDFGetter(sample=sample, trigger=trigger)
    rdf = gtr.get_rdf(per_file=False)

    is_mc = not sample.startswith('DATA_24_')
    _check_branches(rdf, is_ee=True, is_mc=is_mc)

    _print_dotted_branches(rdf)
# ------------------------------------------------
@pytest.mark.parametrize('sample, trigger',
    [
    ('Bu_Kee_eq_btosllball05_DPC'  , 'Hlt2RD_BuToKpEE_MVA'),
    ('Bd_Kstee_eq_btosllball05_DPC', 'Hlt2RD_B0ToKpPimEE_MVA'),
    ('Bu_Kmumu_eq_btosllball05_DPC', 'Hlt2RD_BuToKpMuMu_MVA')])
def test_mcdecaytree(sample : str, trigger : str):
    '''
    Builds dataframe from MCDecayTree
    '''
    with RDFGetter.max_entries(value=10_000):
        gtr = RDFGetter(sample=sample, trigger=trigger, tree='MCDecayTree')
        rdf = gtr.get_rdf(per_file=False)

    rdf      = cast(RDataFrame, rdf)
    nentries = rdf.Count().GetValue()

    log.info(f'Found {nentries} entries')

    assert nentries > 0

    _check_mcdt(rdf=rdf, name=f'mcdt/{sample}')
# ------------------------------------------------
@pytest.mark.parametrize('period'  ,['24c2','24c3','24c4'])
@pytest.mark.parametrize('polarity',['MagUp', 'MagDown'])
@pytest.mark.parametrize('trigger', ['Hlt2RD_BuToKpEE_MVA_ext', 'Hlt2RD_B0ToKpPimEE_MVA_ext'])
def test_ext_trigger(period : str, polarity : str, trigger : str):
    '''
    Test of getter class for combination of analysis and misID trigger
    '''
    sample=f'DATA_24_{polarity}_{period}'
    with RDFGetter.max_entries(-1):
        gtr = RDFGetter(sample=sample, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    _check_ext(rdf)
    _plot_ext(rdf, sample=sample)
# ------------------------------------------------
@pytest.mark.parametrize('trigger', ['Hlt2RD_BuToKpEE_MVA', 'Hlt2RD_B0ToKpPimEE_MVA'])
def test_custom_columns(trigger : str):
    '''
    Tests defining of new custom columns
    '''
    d_def = {'xbrem' : 'int(L1_HASBREMADDED) + int(L2_HASBREMADDED)'}

    with RDFGetter.custom_columns(columns = d_def):
        obj = RDFGetter(trigger=trigger, sample='DATA_24_MagDown_24c2')
        rdf = obj.get_rdf(per_file=False)

    l_col = [ col for col in rdf.GetColumnNames() ]

    assert 'xbrem' in l_col
# ------------------------------------------------
# TODO: This test is very slow, needs to be disabled for now
@pytest.mark.parametrize('sample' , ['Bd_JpsiKst_ee_eq_DPC'  ])
@pytest.mark.parametrize('trigger', ['Hlt2RD_B0ToKpPimEE_MVA'])
def test_block(sample : str, trigger : str):
    '''
    Test of getter class with check for block assignment
    '''
    with RDFGetter.max_entries(value=-1):
        gtr = RDFGetter(sample=sample, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    rdf = _apply_selection(rdf=rdf, trigger=trigger, sample=sample)
    rep = rdf.Report()
    rep.Print()

    _check_block(rdf)

    sample = sample.replace('*', 'p')
    name   = f'block/{sample}_{trigger}'

    _plot_block(rdf=rdf, name=name)
# ------------------------------------------------
@pytest.mark.parametrize('project', ['rk', 'rkst'])
def test_add_truem(project : str):
    '''
    Tests function that adds TRUEM columns to dataframe
    '''
    ana_dir = os.environ['ANADIR']
    path_wc = f'{ana_dir}/Data/{project}/main/*/mc*.root'
    l_path  = glob.glob(path_wc)
    l_path  = sorted(l_path)
    fpath   = l_path[-1]

    cfg     = gut.load_conf(package='rx_data_data', fpath=f'rdf_getter/{project}.yaml')
    rdf     = RDataFrame('DecayTree', fpath)
    rdf     = RDFGetter.add_truem(rdf=rdf, cfg=cfg)

    _check_truem_columns(rdf)
# ------------------------------------------------
@pytest.mark.parametrize('sample', ['Bu_JpsiX_ee_eq_JpsiInAcc', 'Bd_JpsiX_ee_eq_JpsiInAcc', 'Bs_JpsiX_ee_eq_JpsiInAcc'] )
@pytest.mark.parametrize('trigger', ['Hlt2RD_BuToKpEE_MVA', 'Hlt2RD_B0ToKpPimEE_MVA'])
def test_ccbar(sample : str, trigger : str):
    '''
    Tests reading of ccbar + X samples
    '''
    with RDFGetter.max_entries(-1), RDFGetter.skip_adding_columns(True):
        gtr = RDFGetter(sample=sample, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    nentries = rdf.Count().GetValue()

    assert nentries > 0
# ------------------------------------------------
@pytest.mark.parametrize('sample' , ['DATA_24_MagDown_24c2'])
@pytest.mark.parametrize('trigger', ['Hlt2RD_BuToKpEE_MVA', 'Hlt2RD_BuToKpMuMu_MVA' ])
def test_exclude_friends(sample : str, trigger : str):
    '''
    Tests excluding friend trees through a context manager
    '''
    with RDFGetter.exclude_friends(names=['mva']):
        gtr = RDFGetter(sample=sample, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    l_col = [ name for name in rdf.GetColumnNames()        ]
    l_mva = [ name for name in l_col if ('mva_cmb' in name) or ('mva_prc' in name) ]

    assert l_mva == []
# ------------------------------------------------
@pytest.mark.parametrize('sample' , ['DATA_24_MagDown_24c2'])
@pytest.mark.parametrize('trigger', ['Hlt2RD_BuToKpEE_MVA', 'Hlt2RD_BuToKpMuMu_MVA' ])
def test_custom_friend(sample : str, trigger : str):
    '''
    Tests getting data with a custom version for a given tree, either friend or main
    '''
    with RDFGetter.custom_friends(versions={'mva' : 'v7.7'}):
        gtr = RDFGetter(sample=sample, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    _run_default_checks(rdf=rdf, sample=sample, trigger=trigger, test_name='custom_friend')
# ------------------------------------------------
@pytest.mark.parametrize('kind'   , ['data', 'mc'])
@pytest.mark.parametrize('trigger', ['Hlt2RD_BuToKpEE_MVA'])
def test_skip_brem_track_2(kind : str, trigger : str):
    '''
    Tests for electron samples
    '''
    if   kind == 'data':
        sample = 'DATA_24_MagDown_24c2'
    elif kind == 'mc' and trigger == 'Hlt2RD_BuToKpEE_MVA':
        sample = 'Bu_JpsiK_ee_eq_DPC'
    else:
        raise ValueError(f'Invalid kind/trigger: {kind}/{trigger}')

    with RDFGetter.exclude_friends(names=['brem_track_2']):
        gtr = RDFGetter(sample=sample, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    _run_default_checks(
            rdf          =rdf,
            brem_track_2 = False,
            test_name    ='electron',
            trigger      =trigger,
            sample       =sample)
# ------------------------------------------------
@pytest.mark.parametrize('sample, trigger' , [
    ('Bu_KplKplKmn_eq_sqDalitz_DPC'  , 'Hlt2RD_BuToKpEE_MVA_noPID'),
    ('Bu_piplpimnKpl_eq_sqDalitz_DPC', 'Hlt2RD_BuToKpEE_MVA_noPID'),
    ('Bu_JpsiPi_ee_eq_DPC'           , 'Hlt2RD_BuToKpEE_MVA_noPID'),
    ('Bu_Kee_eq_btosllball05_DPC'    , 'Hlt2RD_BuToKpEE_MVA_noPID'),
    ('Bd_Kstee_eq_btosllball05_DPC'  , 'Hlt2RD_BuToKpEE_MVA_noPID'),
    # -------------
    ('Bu_Kmumu_eq_btosllball05_DPC'  , 'Hlt2RD_BuToKpMuMu_MVA_noPID'),
    ('Bd_Kstmumu_eq_btosllball05_DPC', 'Hlt2RD_BuToKpMuMu_MVA_noPID')])
def test_no_pid(sample : str, trigger : str):
    '''
    Tests loading of noPID samples
    '''
    gtr = RDFGetter(sample=sample, trigger=trigger)
    rdf = gtr.get_rdf(per_file=False)
    _run_default_checks(
        rdf         = rdf,
        sample      = sample,
        trigger     = trigger,
        friends     = False,
        brem_track_2= False,
        test_name   = 'no_pid')
# ------------------------------------------------
# TODO: Check for negative numbers
@pytest.mark.parametrize('nthreads', [1, 6])
@pytest.mark.parametrize('trigger', ['Hlt2RD_BuToKpEE_MVA', 'Hlt2RD_B0ToKpPimEE_MVA'])
def test_multithreading(nthreads : int, trigger : str):
    '''
    This will test the context manager used to enable multithreading
    '''
    sample   = 'Bd_Kstee_eq_btosllball05_DPC'
    nentries = 1000 if nthreads == 1 else -1
    nthcheck =    0 if nthreads == 1 else nthreads

    with RDFGetter.multithreading(nthreads=nthreads), \
         RDFGetter.max_entries(value=nentries):

        gtr = RDFGetter(sample=sample, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

        assert GetThreadPoolSize() == nthcheck

        _print_dotted_branches(rdf)
        _check_branches(rdf, is_ee=True, is_mc=True)

        _plot_mva_mass(rdf, f'test_mc/{sample}')
        _plot_mva(rdf     , f'test_mc/{sample}')
        _plot_hop(rdf     , f'test_mc/{sample}')
        _plot_sim(rdf     , f'test_mc/{sample}', particle=   'B')
        _plot_sim(rdf     , f'test_mc/{sample}', particle='Jpsi')

        _plot_mc_qsq(rdf, f'test_multithreading/{sample}', sample)
# ------------------------------------------------
@pytest.mark.parametrize('nthreads', [-3, 0])
def test_multithreading_invalid(nthreads : int):
    '''
    This will test the context manager used to enable multithreading
    with invalid number of threads
    '''
    sample   = 'Bu_JpsiK_ee_eq_DPC'
    with pytest.raises(ValueError):
        with RDFGetter.multithreading(nthreads=nthreads):
            gtr = RDFGetter(sample=sample, trigger='Hlt2RD_BuToKpEE_MVA')
            gtr.get_rdf(per_file=False)
# ------------------------------------------------
def test_multithreading_locked():
    '''
    This will test multithreading with locked class
    '''
    nthreads = 2
    sample   = 'Bu_JpsiK_ee_eq_DPC'

    with pytest.raises(ValueError):
        with RDFGetter.multithreading(nthreads=nthreads):
            with RDFGetter.multithreading(nthreads=nthreads):
                gtr = RDFGetter(sample=sample, trigger='Hlt2RD_BuToKpEE_MVA')
                gtr.get_rdf(per_file=False)
# ------------------------------------------------
@pytest.mark.parametrize('sample', ['Bu_JpsiX_ee_eq_JpsiInAcc'] )
def test_skip_adding_columns(sample : str):
    '''
    Tests reading of ccbar + X samples
    '''
    trigger = 'Hlt2RD_BuToKpEE_MVA'

    gtr_1 = RDFGetter(sample=sample, trigger=trigger)
    rdf_1 = gtr_1.get_rdf(per_file=False)

    with RDFGetter.skip_adding_columns(True):
        gtr_2 = RDFGetter(sample=sample, trigger=trigger)
        rdf_2 = gtr_2.get_rdf(per_file=False)

    assert not isinstance(rdf_1, dict)
    assert not isinstance(rdf_2, dict)

    l_col_1 = [ name for name in rdf_1.GetColumnNames() ]
    l_col_2 = [ name for name in rdf_2.GetColumnNames() ]

    assert len(l_col_1) > len(l_col_2)
# ------------------------------------------------
@pytest.mark.parametrize('sample' , ['DATA_24_MagDown_24c2'])
@pytest.mark.parametrize('trigger', ['Hlt2RD_BuToKpEE_MVA', 'Hlt2RD_BuToKpMuMu_MVA' ])
def test_only_friends(sample : str, trigger : str):
    '''
    Tests the only_friends manager, which allows only a subset of friend trees
    '''
    s_friend = {'mva', 'hop'}
    with RDFGetter.only_friends(s_friend=s_friend):
        gtr = RDFGetter(sample=sample, trigger=trigger)

    assert gtr.friend_trees == s_friend
# ------------------------------------------------
@pytest.mark.parametrize('trigger', ['Hlt2RD_BuToKpEE_MVA', 'Hlt2RD_B0ToKpPimEE_MVA'])
@pytest.mark.parametrize('sample' , ['Bd_Kstee_eq_btosllball05_DPC', 'DATA*'])
@pytest.mark.parametrize('smeared', [True, False])
@pytest.mark.parametrize('q2bin'  , Data.l_q2bin)
def test_selection(
    sample  : str, 
    trigger : str,
    smeared : bool, 
    q2bin   : str):
    '''
    Basic test of selection
    '''
    gtr = RDFGetter(sample=sample, trigger=trigger)
    rdf = gtr.get_rdf(per_file=False)

    d_sel = sel.selection(
        trigger=trigger,
        q2bin  =q2bin,
        process=sample,
        smeared=smeared)

    for cut_name, cut_value in d_sel.items():
        rdf = rdf.Filter(cut_value, cut_name)

    rep = rdf.Report()
    df  = ut.rdf_report_to_df(rep)
    if df is None:
        raise ValueError('Empty cutflow')

    df['sample' ] = sample
    df['smeared'] = smeared
    df['q2bin'  ] = q2bin

    col.Collector.add_dataframe(df=df, test_name='selection')

    _print_dotted_branches(rdf)
# --------------------------
@pytest.mark.parametrize('trigger', ['Hlt2RD_BuToKpEE_MVA', 'Hlt2RD_B0ToKpPimEE_MVA'])
@pytest.mark.parametrize('sample', ['Bd_Kstee_eq_btosllball05_DPC', 'DATA_24_MagDown_24c2'])
@pytest.mark.parametrize('q2bin' , Data.l_q2bin)
def test_full_selection_electron(
    sample  : str, 
    q2bin   : str, 
    trigger : str):
    '''
    Applies full selection to all q2 bins in electron channel
    '''
    with RDFGetter.max_entries(value=100_000):
        gtr = RDFGetter(sample=sample, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    rdf     = sel.apply_full_selection(rdf = rdf, trigger=trigger, q2bin=q2bin, process=sample)

    rep     = rdf.Report()
    rep.Print()

    nentries = rdf.Count().GetValue()

    assert nentries > 0

    _print_dotted_branches(rdf)
# --------------------------
@pytest.mark.parametrize('sample' , ['Bd_Kstmumu_eq_btosllball05_DPC', 'DATA_24_MagDown_24c2'])
@pytest.mark.parametrize('q2bin'  , Data.l_q2bin)
@pytest.mark.parametrize('trigger', ['Hlt2RD_BuToKpMuMu_MVA', 'Hlt2RD_B0ToKpPimMuMu_MVA'])
def test_full_selection_muon(sample : str, q2bin : str, trigger : str):
    '''
    Applies full selection to all q2 bins in muon channel
    '''
    with RDFGetter.max_entries(value=100_000):
        gtr = RDFGetter(sample=sample, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    rdf     = sel.apply_full_selection(rdf = rdf, trigger=trigger, q2bin=q2bin, process=sample)
    rep     = rdf.Report()
    rep.Print()

    nentries = rdf.Count().GetValue()

    assert nentries > 0

    _print_dotted_branches(rdf)
