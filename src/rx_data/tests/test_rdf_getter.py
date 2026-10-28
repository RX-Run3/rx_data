'''
Class testing RDFGetter
'''
import os
import glob
import math

import matplotlib.pyplot as plt
import pandas            as pnd
import pytest
import mplhep
import numpy

from contextlib     import ExitStack
from typing         import cast, Final
from pathlib        import Path
from ROOT           import RDataFrame, RDF, EnableImplicitMT
from dmu            import LogStore
from dmu.plotting   import Plotter2D
from dmu.generic    import utilities as gut
from dmu.rdataframe import utilities as ut

from rx_common      import Component, Cuts, Project, Qsq
from rx_selection   import selection as sel
from rx_data        import collector as col
from rx_data        import RDFGetter
from rx_common      import Trigger

_EMULATED : Final[list[tuple[Component, Component, Trigger]]] = [
    (Component.bdkstkpijpsimm, Component.bskstjpsimm            , Trigger.rkst_mm_os),
    (Component.bdkstkpijpsiee, Component.bskstjpsiee            , Trigger.rkst_ee_os),
    # -------------
    (Component.bdkstkpijpsimm, Component.bdkstkpijpsimm_kpimm_pikmm    , Trigger.rkst_mm_os),
    (Component.bdkstkpijpsiee, Component.bdkstkpijpsiee_kpiee_pikee    , Trigger.rkst_ee_os),
    # -------------
    (Component.bdkstkpijpsimm, Component.bdkstkpijpsimm_kpimm_kmpim , Trigger.rkst_mm_os),
    (Component.bdkstkpijpsiee, Component.bdkstkpijpsiee_kpiee_pikee , Trigger.rkst_ee_os),
]

_MCSS : Final[list[tuple[Component,Trigger]]] = [
    (Component.bpkpee    , Trigger.rk_ee_ss  ),
    (Component.bdkstkpiee, Trigger.rkst_ee_ss),
]

_SIGNALS : Final[list[tuple[Component,Trigger]]] = [
    (Component.bpkpee    , Trigger.rk_ee_os  ),
    (Component.bpkpee    , Trigger.rk_ee_ss  ),
    (Component.bpkpmm    , Trigger.rk_mm_os  ),
    (Component.bdkstkpiee, Trigger.rkst_ee_os),
    (Component.bdkstkpiee, Trigger.rkst_ee_ss),
    (Component.bdkstkpimm, Trigger.rkst_mm_os),
]

_RESONANT_SAMPLES : Final[list[tuple[Component,Trigger]]] = [
    (Component.bppijpsiee    , Trigger.rk_ee_os  ),
    (Component.bpkpjpsiee    , Trigger.rk_ee_os  ),
    (Component.bdkstkpijpsiee, Trigger.rkst_ee_os),
    (Component.bpkpjpsimm    , Trigger.rk_mm_os  ),
    (Component.bdkstkpijpsimm, Trigger.rkst_mm_os),
]

_SEMILEPTONIC_SAMPLES : Final[list[tuple[Component,Trigger]]] = [
    (Component.bpdpiknuee,   Trigger.rk_ee_os),
    (Component.bpdnuknuee,   Trigger.rk_ee_os),
    (Component.bpdnukpiee,   Trigger.rk_ee_os),
]

_DATA_SAMPLES     : Final[list[tuple[Component,Trigger]]] = [
    (Component.data_24_md_c2, Trigger.rk_ee_os  ),
    (Component.data_24_md_c2, Trigger.rkst_ee_os),
    (Component.data_24_md_c2, Trigger.rk_mm_os  ),
    (Component.data_24_md_c2, Trigger.rkst_mm_os),
]

_INCLUSIVE_SAMPLES : Final[list[tuple[Component,Trigger]]] = [
    (Component.bdjpsixee, Trigger.rk_ee_os),
    (Component.bpjpsixee, Trigger.rk_ee_os),
    (Component.bsjpsixee, Trigger.rk_ee_os),
    # ----------
    (Component.bdjpsixmm, Trigger.rk_mm_os),
    (Component.bpjpsixmm, Trigger.rk_mm_os),
    (Component.bsjpsixmm, Trigger.rk_mm_os),
]

# TODO: Need test for default_skip manager
log=LogStore.add_logger('rx_data:test_rdf_getter')

_NBLOCKS : Final[int] = 8
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
        'Jpsi_Mass',
        'B_Mass']

    l_branch_mm = l_branch_common + ['B_Mass', 'Jpsi_Mass']
    l_q2bin     = ['low', 'cen_low', 'central', 'cen_high', 'psi2', 'high']
# --------------------------
@pytest.fixture(scope='module', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('rx_data:test_rdf_getter', 10)
    LogStore.set_level('rx_data:rdf_getter'     , 10)
    LogStore.set_level('rx_data:spec_maker'     , 10)
    LogStore.set_level('rx_data:sample_emulator', 10)
    LogStore.set_level('rx_data:sample_patcher' , 10)

    plt.style.use(mplhep.style.LHCb2)

    with RDFGetter.alignment_check():
        EnableImplicitMT(2)
        yield
# ------------------------------------------------
def _check_truem_columns(rdf : RDF.RNode):
    l_name = [ name.c_str() for name in rdf.GetColumnNames() if name.c_str().endswith('_TRUEM') ]
    d_data = rdf.AsNumpy(l_name)
    df     = pnd.DataFrame(d_data)
    nnan   = df.isna().sum().sum()
    ntot   = len(df)

    if nnan > 0:
        raise ValueError(f'Found {nnan}/{ntot} NaNs in dataframe')
# ------------------------------------------------
def _check_block(rdf : RDF.RNode) -> None:
    arr_block = rdf.AsNumpy(['block'])['block']

    assert numpy.all(arr_block >=        0)
    assert numpy.all(arr_block <= _NBLOCKS)
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

    l_name = [ _name_from_raw_name(name=name.c_str()) for name in rdf.GetColumnNames() ]

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
    l_name = [ name.c_str() for name in rdf.GetColumnNames() ]

    for name in l_name:
        if '.' not in name:
            continue

        log.info(name)
# ------------------------------------------------
def _plot_mva_mass(rdf : RDF.RNode, test : str, out_dir : Path) -> None:
    test_dir = f'{out_dir}/{test}'
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
def _plot_block(rdf : RDF.RNode, name : str, out_dir : Path) -> None:
    arr_block = rdf.AsNumpy(['block'])['block']

    os.makedirs(f'{out_dir}/{name}', exist_ok=True)

    plt.hist(arr_block, bins=30)
    plt.savefig(f'{out_dir}/{name}/block.png')
    plt.close()
# ------------------------------------------------
def _plot_bmass(
    rdf         : RDF.RNode,
    trigger     : Trigger,
    brem_track_2: bool,
    out_dir     : Path,
    test_name   : str) -> None:

    test_dir = f'{out_dir}/{test_name}'
    os.makedirs(test_dir, exist_ok=True)

    minx = 4500
    maxx = 6000
    if trigger.is_electron and brem_track_2:
        masses = ['B_Mass_smr', 'B_M']
    else:
        masses = ['B_M']

    data = rdf.AsNumpy(masses)
    df   = pnd.DataFrame(data)

    df.to_json(f'{test_dir}/bmass.json', indent=2)
    df.plot.hist(range=[minx, maxx], bins=100, histtype='step')

    plt.title(test_name)
    plt.legend()
    plt.savefig(f'{test_dir}/bmass.png')
    plt.close()
# ------------------------------------------------
def _plot_q2_track(rdf : RDF.RNode, sample : str, out_dir : Path) -> None:
    test_dir = f'{out_dir}/{sample}'
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
def _plot_sim(rdf : RDF.RNode, test : str, particle : str, out_dir : Path) -> None:
    test_dir = f'{out_dir}/{test}'
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
def _plot_mva(rdf : RDF.RNode, test : str, out_dir : Path) -> None:
    test_dir = f'{out_dir}/{test}'
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
def _plot_hop(rdf : RDF.RNode, test : str, out_dir : Path) -> None:
    test_dir = f'{out_dir}/{test}'
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
        trigger  : Trigger,
        sample   : Component,
        override : None | dict[Cuts,str] = None) -> RDF.RNode:
    '''
    Apply full selection but q2 and mass
    '''
    d_sel = sel.selection(
        trigger=trigger,
        q2bin  =Qsq.jpsi,
        process=sample)

    if override is not None:
        d_sel.update(override)

    for cut_name, cut_expr in d_sel.items():
        if cut_name in ['mass', 'q2']:
            continue
        rdf = rdf.Filter(cut_expr, cut_name)

    return rdf
# ------------------------------------------------
def _plot_brem_track_2(rdf : RDF.RNode, test : str, tree : str, out_dir : Path) -> None:
    test_dir = f'{out_dir}/{test}/{tree}'
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
def _plot_mc_qsq(rdf : RDF.RNode, test : str, sample : str, out_dir : Path) -> None:
    test_dir = f'{out_dir}/{test}'
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
def _plot_ext(rdf : RDF.RNode, sample : str, out_dir : Path) -> None:
    cfg = {
            'saving'   : {'plt_dir' : f'{out_dir}/ext'},
            'general'  : {'size' : [20, 10]},
            'plots_2d' :
            [['L1_PIDe', 'L2_PIDe', 'weight', f'PIDe_wgt_{sample}', True],
             ['L1_PIDe', 'L2_PIDe',     None, f'PIDe_raw_{sample}', True]],
            'axes' :
            {
                'L1_PIDe' : {'binning' : [-5, 13, 60], 'label': r'$\Delta LL(e^+)$'},
                'L2_PIDe' : {'binning' : [-5, 13, 60], 'label': r'$\Delta LL(e^-)$'},
                },
            }

    ptr=Plotter2D(rdf=rdf, cfg=cfg)
    ptr.run()
# ------------------------------------------------
def _check_ext(rdf : RDF.RNode) -> None:
    rdf_ana = rdf.Filter('L1_PIDe > 1 && L2_PIDe > 1')
    rdf_mis = rdf.Filter('L1_PIDe < 1 || L2_PIDe < 1')

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
def _check_mcdt(rdf : RDF.RNode, name : str, out_dir : Path) -> None:
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

    test_dir = f'{out_dir}/{name}'
    os.makedirs(test_dir, exist_ok=True)

    plt.hist(arr_q2, bins=60, range=(0, 22), histtype='step')
    plt.savefig(f'{test_dir}/q2.png')
    plt.close()
# ------------------------------------------------
def _check_total_charge(rdf : RDF.RNode, trigger : Trigger) -> None:
    '''
    Check branch `total_charge`
    '''
    TARGET = 'total_charge'

    columns = [ col.c_str() for col in rdf.GetColumnNames() ]

    if TARGET not in columns:
        raise ValueError(f'No {TARGET} column found')

    arr_charge = rdf.AsNumpy([TARGET])[TARGET]
    charges    = set(arr_charge.tolist())

    if trigger.project == Project.rkst:
        assert charges == {+2, -2}

    # TODO: +1, -1 candidates seem to be missing
    # Need to check this
    if trigger.project == Project.rk:
        assert charges == {+3, -3}
# ------------------------------------------------
def _run_default_checks(
    rdf          : RDF.RNode,
    test_name    : str,
    trigger      : Trigger,
    sample       : Component,
    tmp_path     : Path,
    friends      : bool = True,
    brem_track_2 : bool = True) -> None:

    _check_branches(
        rdf,
        is_ee        = 'MuMu' not in trigger,
        is_mc        = False,
        friends      = friends,
        brem_track_2 = brem_track_2)

    _plot_bmass(
        out_dir      = tmp_path,
        brem_track_2 = brem_track_2,
        rdf          = rdf,
        trigger      = trigger,
        test_name    = f'{test_name}_{sample}')

    if not friends: # Not friends no checks below
        return

    _check_mva_scores(rdf=rdf)
    _plot_mva_mass(rdf, f'{test_name}_{sample}', out_dir = tmp_path)
    _plot_mva(rdf     , f'{test_name}_{sample}', out_dir = tmp_path)
    _plot_hop(rdf     , f'{test_name}_{sample}', out_dir = tmp_path)
# ------------------------------------------------
# Basic tests
# ------------------------------------------------
def test_consistent_loop():
    '''
    Test that we get the same number of entries if triggering
    loop multiple times
    '''
    component = Component.bppijpsiee
    trigger   = Trigger.rk_ee_os
    q2bin     = Qsq.jpsi

    with RDFGetter.max_entries(value=1000):
        gtr = RDFGetter(sample=component, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    rdf     = sel.apply_full_selection(
        rdf    = rdf, 
        trigger=trigger, 
        q2bin  =q2bin, 
        process=component)

    values    = []
    for _ in range(10):
        nentries = rdf.Count()
        rep      = rdf.Report()

        rep.Print()
        values.append(nentries.GetValue()) 
        log.info('')

    log.info(f'Found entries: {values}')

    assert len(set(values)) == 1
# ------------------------------------------------
def test_consistent_build():
    '''
    Test that we get the same number of entries if 
    building dataframe multiple times
    '''
    component = Component.bppijpsiee
    trigger   = Trigger.rk_ee_os
    q2bin     = Qsq.jpsi

    values    = []
    for _ in range(10):
        with RDFGetter.max_entries(value=1000):
            gtr = RDFGetter(sample=component, trigger=trigger)
            rdf = gtr.get_rdf(per_file=False)

        rdf     = sel.apply_full_selection(
            rdf    = rdf, 
            trigger=trigger, 
            q2bin  =q2bin, 
            process=component)

        nentries = rdf.Count().GetValue()
        values.append(nentries) 

    log.info(f'Found entries: {values}')

    assert len(set(values)) == 1
# ------------------------------------------------
@pytest.mark.basic
@pytest.mark.parametrize('sample, trigger',
    [(Component.bpkpee    , Trigger.rk_ee_os),
     (Component.bpkpmm    , Trigger.rk_mm_os),
     (Component.bdkstkpiee, Trigger.rkst_ee_os),
     (Component.bdkstkpimm, Trigger.rkst_mm_os)])
def test_mcdecaytree(
    sample  : Component,
    trigger : Trigger,
    tmp_path: Path):
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

    _check_mcdt(rdf=rdf, name=f'mcdt/{sample}', out_dir = tmp_path)
# ------------------------------------------------
@pytest.mark.basic
@pytest.mark.parametrize('sample' , [Component.bdkstkpiee, Component.bdkstkpijpsiee])
@pytest.mark.parametrize('trigger', [Trigger.rk_ee_os, Trigger.rkst_ee_os])
def test_mc_ee(
    sample  : Component,
    trigger : Trigger,
    tmp_path: Path):
    '''
    Test of getter class in mc
    '''
    if sample == Component.bdkstkpijpsiee and trigger == Trigger.rk_ee_os:
        return

    with RDFGetter.max_entries(value=10_000):
        gtr = RDFGetter(sample=sample, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    _plot_sim(rdf, f'test_mc/{sample}', out_dir = tmp_path, particle=   'B')
    _plot_sim(rdf, f'test_mc/{sample}', out_dir = tmp_path, particle='Jpsi')

    if 'B0ToKpPim' in trigger:
        return

    _print_dotted_branches(rdf)
    _check_branches(rdf, is_ee=True, is_mc=sample.is_mc)

    _plot_mc_qsq(rdf, f'test_mc/{sample}', sample, out_dir = tmp_path)
    _plot_mva_mass(rdf, f'test_mc/{sample}', out_dir = tmp_path)
    _plot_mva(rdf     , f'test_mc/{sample}', out_dir = tmp_path)
    _plot_hop(rdf     , f'test_mc/{sample}', out_dir = tmp_path)
# ------------------------------------------------
@pytest.mark.basic
@pytest.mark.parametrize('sample' , [Component.bpkpmm, Component.bdkstkpijpsimm])
@pytest.mark.parametrize('trigger', [Trigger.rk_mm_os, Trigger.rkst_mm_os])
def test_mc_mm(
    sample  : Component,
    trigger : Trigger,
    tmp_path: Path):
    '''
    Test of getter class in mc
    '''
    if sample == Component.bdkstkpijpsimm and trigger == Trigger.rk_mm_os:
        return

    with RDFGetter.max_entries(value=10_000):
        gtr = RDFGetter(sample=sample, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    _plot_sim(rdf, f'test_mc/{sample}', out_dir = tmp_path, particle=   'B')
    _plot_sim(rdf, f'test_mc/{sample}', out_dir = tmp_path, particle='Jpsi')

    if 'B0ToKpPim' in trigger:
        return

    _print_dotted_branches(rdf)
    _check_branches(rdf, is_ee=True, is_mc=sample.is_mc)

    _plot_mc_qsq(rdf, f'test_mc/{sample}', sample, out_dir = tmp_path)
    _plot_mva_mass(rdf, f'test_mc/{sample}', out_dir = tmp_path)
    _plot_mva(rdf     , f'test_mc/{sample}', out_dir = tmp_path)
    _plot_hop(rdf     , f'test_mc/{sample}', out_dir = tmp_path)
# ------------------------------------------------
@pytest.mark.basic
@pytest.mark.parametrize(
    'sample' , [
    Component.data_24_md_c2,
    Component.data_24_md_c3,
    Component.data_24_md_c4,
    Component.data_24_mu_c2,
    Component.data_24_mu_c3,
    Component.data_24_mu_c4])
@pytest.mark.parametrize('trigger',
    [Trigger.rk_ee_os,
     Trigger.rkst_ee_os,
     Trigger.rk_mm_os,
     Trigger.rkst_mm_os])
def test_data(
    sample  : Component,
    trigger : Trigger,
    tmp_path: Path):
    '''
    Test of getter class in data
    '''
    with RDFGetter.max_entries(value=1000):
        gtr = RDFGetter(sample=sample, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    rdf = _apply_selection(rdf=rdf, trigger=trigger, sample=sample)
    rep = rdf.Report()
    rep.Print()

    if 'B0ToKpPim' in trigger:
        return

    _run_default_checks(
        rdf      = rdf,
        sample   = sample,
        trigger  = trigger,
        tmp_path = tmp_path,
        test_name= f'data_{sample}_{trigger}')
# ------------------------------------------------
# ------------------------------------------------
def test_cocktail():
    '''
    Test that cocktail samples are actually merged
    '''
    gtr_k1 = RDFGetter(sample = Component.bpk1kpipiee, trigger = Trigger.rkst_ee_os)
    rdf_k1 = gtr_k1.get_rdf(per_file = False)

    gtr_k2 = RDFGetter(sample = Component.bpk2kpipiee, trigger = Trigger.rkst_ee_os)
    rdf_k2 = gtr_k2.get_rdf(per_file = False)

    gtr_kx = RDFGetter(sample = Component.bpkxkpipiee, trigger = Trigger.rkst_ee_os)
    rdf_kx = gtr_kx.get_rdf(per_file = False)

    column = 'EVENTNUMBER'

    evt_k1 = rdf_k1.AsNumpy([column])[column]
    evt_k2 = rdf_k2.AsNumpy([column])[column]
    evt_kx = rdf_kx.AsNumpy([column])[column]
    evt_kx = numpy.sort(evt_kx)

    evt_ky = numpy.concatenate([evt_k1, evt_k2])
    evt_ky = numpy.sort(evt_ky)

    # These will be different almost always
    assert evt_k1.shape != evt_k2.shape

    log.debug(f'K1: {evt_k1.shape}')
    log.debug(f'K2: {evt_k2.shape}')
    log.debug(f'KX: {evt_kx.shape}')
    log.debug(f'KY: {evt_ky.shape}')

    assert numpy.array_equal(evt_kx, evt_ky)
# ------------------------------------------------
@pytest.mark.parametrize('component, trigger', _MCSS)
def test_mc_ss(component : Component, trigger : Trigger, tmp_path : Path):
    '''
    Tests for electron samples
    '''
    with RDFGetter.max_entries(-1):
        gtr = RDFGetter(
            sample =component,
            trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    with sel.custom_selection(d_sel = {Cuts.truth : '(1)'}):
        rdf = sel.apply_full_selection(
            rdf     = rdf,
            q2bin   = Qsq.central,
            process = component,
            trigger = trigger)

    rep = rdf.Report()
    rep.Print()

    _check_total_charge(
        rdf     = rdf,
        trigger = trigger)

    _run_default_checks(
        rdf      = rdf,
        test_name= 'signal',
        trigger  = trigger,
        tmp_path = tmp_path,
        sample   = component)
# ------------------------------------------------
@pytest.mark.parametrize('component, trigger', _SIGNALS)
def test_signal(component : Component, trigger : Trigger, tmp_path : Path):
    '''
    Tests for electron samples
    '''
    max_entries = -1 if trigger.is_ss else 50_000
    with RDFGetter.max_entries(max_entries):
        gtr = RDFGetter(
            sample =component,
            trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    _run_default_checks(
        rdf      = rdf,
        test_name= 'signal',
        trigger  = trigger,
        tmp_path = tmp_path,
        sample   = component)
# ------------------------------------------------
@pytest.mark.parametrize('per_file', [True, False])
@pytest.mark.parametrize('trigger' , [Trigger.rk_ee_os, Trigger.rkst_ee_os])
def test_guid(trigger : Trigger, per_file : bool):
    '''
    Tests retrieval of unique identifier for underlying data
    '''
    sam1 = Component.bdkstkpiee
    sam2 = Component.bpkstkpiee

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
@pytest.mark.parametrize('sample'   , [Component.bdkstkpiee])
@pytest.mark.parametrize('trigger'  , [Trigger.rk_ee_os, Trigger.rkst_ee_os])
@pytest.mark.parametrize('requested', [1_000, 10_000, 20_000])
def test_max_entries(
    sample    : Component,
    requested : int,
    trigger   : Trigger):
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
@pytest.mark.parametrize(
    'sample, trigger',
    [
    (Component.data_24_md_c2, Trigger.rk_ee_os),
    (Component.bpkpee       , Trigger.rk_ee_os),
    (Component.data_24_md_c2, Trigger.rk_mm_os),
    (Component.bpkpmm       , Trigger.rk_mm_os),
    # ------------------
    (Component.data_24_md_c2, Trigger.rkst_ee_os),
    (Component.bdkstkpiee   , Trigger.rkst_ee_os),
    (Component.data_24_md_c2, Trigger.rkst_mm_os),
    (Component.bdkstkpimm   , Trigger.rkst_mm_os),
     ])
def test_per_file(
    sample   : Component,
    trigger  : Trigger,
    tmp_path : Path):
    '''
    Test of per_file flag set to True
    '''
    with RDFGetter.max_entries(1000):
        gtr   = RDFGetter(sample=sample, trigger=trigger)
        d_rdf = gtr.get_rdf(per_file=True)

    for val, rdf in d_rdf.items():
        name = hash(val)
        name = abs(name)
        name = str(name)
        name = name[:10]

        # TODO: Remove when we have friend trees for RKst
        if 'B0ToKpPim' in trigger:
            continue

        _check_branches(rdf, is_ee = trigger.is_electron, is_mc = sample.is_mc)

        _plot_mva_mass(rdf, f'{name}_{sample}', out_dir = tmp_path)
        _plot_mva(rdf     , f'{name}_{sample}', out_dir = tmp_path)
        _plot_hop(rdf     , f'{name}_{sample}', out_dir = tmp_path)
# ------------------------------------------------
@pytest.mark.parametrize('kind'   , ['data', 'mc'])
@pytest.mark.parametrize('trigger', [Trigger.rk_ee_os, Trigger.rkst_ee_os])
def test_electron(kind : str, trigger : Trigger, tmp_path : Path):
    '''
    Tests for electron samples
    '''
    if   kind == 'data':
        sample = Component.data_24_md_c2
    elif kind == 'mc':
        sample = Component.bdkstkpiee
    else:
        raise ValueError(f'Invalid kind/trigger: {kind}/{trigger}')

    with RDFGetter.max_entries(50_000):
        gtr = RDFGetter(sample=sample, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    if 'B0ToKpPim' in trigger:
        return

    _run_default_checks(
        rdf      = rdf,
        test_name= 'electron',
        trigger  = trigger,
        tmp_path = tmp_path,
        sample   = sample)
# ------------------------------------------------
@pytest.mark.parametrize('sample' , [Component.data_24_md_c2, Component.bdkstkpiee])
@pytest.mark.parametrize('trigger', [Trigger.rk_ee_os, Trigger.rkst_ee_os])
def test_q2_track_electron(
    sample   : Component,
    trigger  : Trigger,
    tmp_path : Path):
    '''
    Checks the distributions of q2_track vs normal q2
    '''
    gtr = RDFGetter(sample=sample, trigger=trigger)
    rdf = gtr.get_rdf(per_file=False)
    rdf = _apply_selection(rdf=rdf, trigger=trigger, sample=sample)
    rep = rdf.Report()
    rep.Print()

    _plot_q2_track(rdf, sample, out_dir = tmp_path)

    if 'B0ToKpPim' in trigger:
        return

    _check_branches(rdf, is_ee=True, is_mc = sample.is_mc)
# ------------------------------------------------
@pytest.mark.parametrize('sample' , [Component.data_24_md_c2, Component.bdkstkpimm])
@pytest.mark.parametrize('trigger', [Trigger.rk_mm_os, Trigger.rkst_mm_os])
def test_q2_track_muon(
    sample   : Component,
    trigger  : Trigger,
    tmp_path : Path):
    '''
    Checks the distributions of q2_track vs normal q2
    '''
    gtr = RDFGetter(sample=sample, trigger=trigger)
    rdf = gtr.get_rdf(per_file=False)
    rdf = _apply_selection(rdf=rdf, trigger=trigger, sample=sample)
    rep = rdf.Report()
    rep.Print()

    identifier = f'{trigger}_{sample}'

    _plot_q2_track(rdf, identifier, out_dir = tmp_path)

    if 'B0ToKpPim' in trigger:
        return

    _check_branches(rdf, is_ee=False, is_mc=sample.is_mc)
# ------------------------------------------------
@pytest.mark.parametrize('sample' , [Component.data_24_md_c2, Component.bpkpjpsiee])
@pytest.mark.parametrize('trigger', [Trigger.rk_ee_os])
def test_brem_track_2(
    sample  : Component,
    trigger : Trigger,
    tmp_path: Path):
    '''
    Test brem_track_2 correction
    '''
    gtr = RDFGetter(sample=sample, trigger=trigger)
    rdf = gtr.get_rdf(per_file=False)
    rdf = _apply_selection(rdf=rdf, trigger=trigger, override = {Cuts.mass : 'B_const_mass_M > 5160'}, sample=sample)
    rep = rdf.Report()
    rep.Print()

    _check_branches(rdf, is_ee=True, is_mc=sample.is_mc)

    _plot_brem_track_2(rdf, sample, 'brem_track_2', out_dir = tmp_path)
# ------------------------------------------------
@pytest.mark.parametrize('sample' , [Component.data_24_md_c2, Component.bdkstkpiee])
@pytest.mark.parametrize('trigger', [Trigger.rk_ee_os, Trigger.rkst_ee_os])
def test_check_vars(sample : Component, trigger : Trigger):
    '''
    Checks that variables from:

    - Friend trees
    - Added branches, e.g. L*_TRACK_P/ETA, etc

    Can be accessed
    '''
    gtr = RDFGetter(sample=sample, trigger=trigger)
    rdf = gtr.get_rdf(per_file=False)

    _check_branches(rdf, is_ee=True, is_mc=sample.is_mc)

    _print_dotted_branches(rdf)
# ------------------------------------------------
@pytest.mark.parametrize('sample' , Component.data_24.subsamples)
@pytest.mark.parametrize('trigger', [Trigger.rk_ee_nopid, Trigger.rkst_ee_nopid])
def test_ext_trigger(
    sample   : Component, 
    trigger  : Trigger, 
    tmp_path : Path):
    '''
    Test of getter class for combination of analysis and misID trigger
    '''
    ctx_1   = RDFGetter.max_entries(-1)

    with ExitStack() as stack:
        stack.enter_context(ctx_1)

        gtr = RDFGetter(sample=sample, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    _check_ext(rdf)
    _plot_ext(rdf, sample=sample, out_dir=tmp_path)
# ------------------------------------------------
@pytest.mark.parametrize('trigger', [Trigger.rk_ee_os, Trigger.rkst_ee_os])
def test_custom_columns(trigger : Trigger):
    '''
    Tests defining of new custom columns
    '''
    d_def = {'xbrem' : 'int(L1_HASBREMADDED) + int(L2_HASBREMADDED)'}
    with RDFGetter.custom_columns(columns = d_def):
        obj = RDFGetter(trigger=trigger, sample=Component.data_24_md_c2)
        rdf = obj.get_rdf(per_file=False)

    l_col = [ col.c_str() for col in rdf.GetColumnNames() ]

    assert 'xbrem' in l_col
# ------------------------------------------------
@pytest.mark.parametrize('sample, trigger', _RESONANT_SAMPLES)
def test_no_friends_mc(
    sample  : Component,
    trigger : Trigger,
    tmp_path: Path):
    '''
    Test loading files with out any friend
    '''
    with RDFGetter.only_friends(s_friend = set()):
        gtr = RDFGetter(sample=sample, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    nentries = rdf.Count()

    _check_block(rdf = rdf)

    name = f'no_friends/{sample}_{trigger}'

    _plot_block(rdf=rdf, name=name, out_dir = tmp_path)

    assert nentries.GetValue() > 0
# ------------------------------------------------
@pytest.mark.parametrize('sample, trigger', _RESONANT_SAMPLES)
def test_blocks_rs(
    sample  : Component,
    trigger : Trigger,
    tmp_path: Path):
    '''
    Check that files contain 'block' column
    '''
    q2bin = Qsq.jpsi
    with RDFGetter.exclude_friends(names = []):
        gtr = RDFGetter(sample=sample, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

        rdf = sel.apply_full_selection(
            rdf     = rdf,
            process = sample,
            trigger = trigger,
            q2bin   = q2bin)

    nentries = rdf.Count()

    _check_block(rdf = rdf)

    name   = f'no_friends/{sample}_{trigger}'

    _plot_block(rdf=rdf, name=name, out_dir = tmp_path)

    assert nentries.GetValue() > 0
# ------------------------------------------------
@pytest.mark.parametrize('sample, trigger', _SEMILEPTONIC_SAMPLES)
def test_blocks_sl(
    sample  : Component,
    trigger : Trigger,
    tmp_path: Path):
    '''
    Check that files contain 'block' column
    '''
    gtr = RDFGetter(sample=sample, trigger=trigger)
    rdf = gtr.get_rdf(per_file=False)

    nentries = rdf.Count()

    _check_block(rdf = rdf)

    name   = f'no_friends/{sample}_{trigger}'

    _plot_block(rdf=rdf, name=name, out_dir = tmp_path)

    assert nentries.GetValue() > 0
# ------------------------------------------------
@pytest.mark.parametrize('sample, trigger', _DATA_SAMPLES)
def test_no_friends_dt(
    sample  : Component,
    trigger : Trigger,
    tmp_path: Path):
    '''
    Test loading files with out any friend
    '''
    with RDFGetter.only_friends(s_friend = set()):
        gtr = RDFGetter(sample=sample, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    assert rdf.Count().GetValue() > 0

    _check_block(rdf)

    name   = f'no_friends/{sample}_{trigger}'

    _plot_block(rdf=rdf, name=name, out_dir = tmp_path)
# ------------------------------------------------
@pytest.mark.parametrize('sample' , [Component.bdkstkpijpsiee])
@pytest.mark.parametrize('trigger', [Trigger.rkst_ee_os])
def test_block(
    sample  : Component,
    trigger : Trigger,
    tmp_path: Path):
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

    name   = f'block/{sample}_{trigger}'

    _plot_block(rdf=rdf, name=name, out_dir = tmp_path)
# ------------------------------------------------
@pytest.mark.parametrize('project', [Project.rk, Project.rkst])
def test_add_truem(project : Project):
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
@pytest.mark.parametrize('sample, trigger', _INCLUSIVE_SAMPLES)
def test_ccbar(sample : Component, trigger : Trigger):
    '''
    Tests reading of ccbar + X samples
    '''
    with RDFGetter.max_entries(10_000):
        gtr = RDFGetter(sample=sample, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    nentries = rdf.Count().GetValue()

    assert nentries > 0
# ------------------------------------------------
@pytest.mark.parametrize('sample' , [Component.data_24_md_c2])
@pytest.mark.parametrize('trigger', [Trigger.rk_ee_os, Trigger.rk_mm_os])
def test_exclude_friends(sample : Component, trigger : Trigger):
    '''
    Tests excluding friend trees through a context manager
    '''
    trigger = Trigger(trigger)
    with RDFGetter.exclude_friends(names=['mva']):
        gtr = RDFGetter(sample=sample, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    l_col = [ name.c_str() for name in rdf.GetColumnNames()        ]
    l_mva = [ name         for name in l_col if ('mva_cmb' in name) or ('mva_prc' in name) ]

    assert l_mva == []
# ------------------------------------------------
@pytest.mark.parametrize('kind'   , ['data', 'mc'])
@pytest.mark.parametrize('trigger', [Trigger.rk_ee_os])
def test_skip_brem_track_2(kind : str, trigger : Trigger, tmp_path : Path):
    '''
    Tests for electron samples
    '''
    if   kind == 'data':
        sample = Component.data_24_md_c2
    elif kind == 'mc' and trigger == Trigger.rk_ee_os:
        sample = Component.bpkpjpsiee
    else:
        raise ValueError(f'Invalid kind/trigger: {kind}/{trigger}')

    with RDFGetter.exclude_friends(names=['brem_track_2']):
        gtr = RDFGetter(sample=sample, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    _run_default_checks(
        rdf          = rdf,
        brem_track_2 = False,
        test_name    = 'electron',
        trigger      = trigger,
        tmp_path     = tmp_path,
        sample       = sample)
# ------------------------------------------------
@pytest.mark.parametrize('sample' , [Component.data_24_md_c2])
@pytest.mark.parametrize('trigger', [Trigger.rk_ee_os, Trigger.rk_mm_os])
def test_custom_friend(
    sample  : Component,
    trigger : Trigger,
    tmp_path: Path):
    '''
    Tests getting data with a custom version for a given tree, either friend or main
    '''
    trigger = Trigger(trigger)
    with RDFGetter.custom_friends(versions={'mva' : 'v9'}):
        gtr = RDFGetter(sample=sample, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    _run_default_checks(rdf=rdf, sample=sample, trigger=trigger, test_name='custom_friend', tmp_path = tmp_path)
# ------------------------------------------------
@pytest.mark.parametrize('sample, trigger' , [
    (Component.bpkkk     , Trigger.rk_ee_nopid),
    (Component.bpkpipi   , Trigger.rk_ee_nopid),
    (Component.bppijpsiee, Trigger.rk_ee_nopid),
    (Component.bpkpee    , Trigger.rk_ee_nopid),
    # -------------
    (Component.bpkpmm    , Trigger.rk_mm_nopid),
])
def test_no_pid(
    sample  : Component,
    trigger : Trigger,
    tmp_path: Path):
    '''
    Tests loading of noPID samples
    '''
    gtr = RDFGetter(sample=sample, trigger=trigger)
    rdf = gtr.get_rdf(per_file=False)
    _run_default_checks(
        rdf         = rdf,
        sample      = sample,
        trigger     = trigger,
        tmp_path    = tmp_path,
        friends     = False,
        brem_track_2= False,
        test_name   = 'no_pid')
# ------------------------------------------------
@pytest.mark.parametrize('sample', [Component.bpjpsixee] )
def test_skip_adding_columns(sample : Component):
    '''
    Tests reading of ccbar + X samples
    '''
    gtr_1 = RDFGetter(sample=sample, trigger=Trigger.rk_ee_os)
    rdf_1 = gtr_1.get_rdf(per_file=False)

    with RDFGetter.skip_adding_columns(True):
        gtr_2 = RDFGetter(sample=sample, trigger=Trigger.rk_ee_os)
        rdf_2 = gtr_2.get_rdf(per_file=False)

    assert not isinstance(rdf_1, dict)
    assert not isinstance(rdf_2, dict)

    l_col_1 = [ name.c_str() for name in rdf_1.GetColumnNames() ]
    l_col_2 = [ name.c_str() for name in rdf_2.GetColumnNames() ]

    assert len(l_col_1) > len(l_col_2)
# ------------------------------------------------
@pytest.mark.parametrize('sample' , [Component.data_24_md_c2])
@pytest.mark.parametrize('trigger', [Trigger.rk_ee_os, Trigger.rk_mm_os])
def test_only_friends(sample : Component, trigger : Trigger):
    '''
    Tests the only_friends manager, which allows only a subset of friend trees
    '''
    s_friend = {'mva', 'hop'}
    with RDFGetter.only_friends(s_friend=s_friend):
        gtr = RDFGetter(sample=sample, trigger=trigger)

    assert gtr.friend_trees == s_friend
# ------------------------------------------------
@pytest.mark.parametrize('trigger', [Trigger.rk_ee_os    , Trigger.rkst_ee_os])
@pytest.mark.parametrize('sample' , [Component.bdkstkpiee, Component.data_24])
@pytest.mark.parametrize('smeared', [True, False])
@pytest.mark.parametrize('q2bin'  , [Qsq.low, Qsq.central, Qsq.jpsi, Qsq.psi2, Qsq.high])
def test_selection(
    sample  : Component,
    trigger : Trigger,
    smeared : bool,
    q2bin   : Qsq):
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
@pytest.mark.parametrize('component' , [Component.bdkstkpimm, Component.data_24_md_c2])
@pytest.mark.parametrize('q2bin'     , Data.l_q2bin)
@pytest.mark.parametrize('trigger'   , [Trigger.rk_mm_os, Trigger.rkst_mm_os])
def test_full_selection_muon(
        component : Component,
        q2bin     : Qsq,
        trigger   : Trigger):
    '''
    Applies full selection to all q2 bins in muon channel
    '''
    with RDFGetter.max_entries(value=100_000):
        gtr = RDFGetter(sample=component, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    rdf     = sel.apply_full_selection(rdf = rdf, trigger=trigger, q2bin=q2bin, process=component)
    rep     = rdf.Report()
    rep.Print()

    nentries = rdf.Count().GetValue()

    assert nentries > 0

    _print_dotted_branches(rdf)
# --------------------------
@pytest.mark.parametrize('trigger'  , [Trigger.rk_ee_os    , Trigger.rkst_ee_os])
@pytest.mark.parametrize('component', [Component.bdkstkpiee, Component.data_24_md_c2])
@pytest.mark.parametrize('q2bin'    , Data.l_q2bin)
def test_full_selection_electron(
    component : Component,
    q2bin     : Qsq,
    trigger   : Trigger):
    '''
    Applies full selection to all q2 bins in electron channel
    '''
    with RDFGetter.max_entries(value=100_000):
        gtr = RDFGetter(sample=component, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    rdf     = sel.apply_full_selection(rdf = rdf, trigger=trigger, q2bin=q2bin, process=component)

    rep     = rdf.Report()
    rep.Print()

    nentries = rdf.Count().GetValue()

    assert nentries > 0

    _print_dotted_branches(rdf)
# --------------------------
@pytest.mark.parametrize('trigger'  , [Trigger.rkst_ee_os])
@pytest.mark.parametrize('component', [Component.bpk1kpipiee, Component.bpk2kpipiee, Component.bpkxkpipiee])
@pytest.mark.parametrize('q2bin'    , Data.l_q2bin)
def test_full_selection_electron_prec(
    component : Component,
    q2bin     : Qsq,
    trigger   : Trigger,
    tmp_path  : Path):
    '''
    Applies full selection to part reco electron sample
    '''
    with RDFGetter.max_entries(value=100_000):
        gtr = RDFGetter(sample=component, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    rdf     = sel.apply_full_selection(
        rdf     = rdf,
        trigger = trigger,
        q2bin   = q2bin,
        process = component,
        out_path= tmp_path,
    )
    rep     = rdf.Report()
    rep.Print()

    nentries = rdf.Count().GetValue()

    assert nentries > 0

    _print_dotted_branches(rdf)
# --------------------------
@pytest.mark.parametrize('trigger'   , [
    Trigger.rk_mm_ss, Trigger.rkst_mm_ss,
    Trigger.rk_ee_ss, Trigger.rkst_ee_ss])
def test_same_sign(trigger   : Trigger):
    '''
    Applies full selection to all q2 bins in muon channel
    '''
    COLUMN_NAME = 'total_charge'
    with RDFGetter.max_entries(value=1000):
        gtr = RDFGetter(sample=Component.data_24, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    columns = [ col.c_str() for col in rdf.GetColumnNames() ]
    assert COLUMN_NAME in columns

    tot_charge = rdf.AsNumpy([COLUMN_NAME])[COLUMN_NAME]

    values, counts = numpy.unique(tot_charge, return_counts=True)
    log.info(30 * '-')
    log.info('Frequencies')
    log.info(30 * '-')
    for value, count in zip(values, counts, strict = True):
        log.info(f'{value:<20}{count:<20}')
    log.info(30 * '-')

    tot_charge = tot_charge.tolist()
    tot_charge = set(tot_charge)

    if trigger in {Trigger.rk_ee_ss, Trigger.rk_mm_ss}:
        assert tot_charge == {-1, -3, +1, +3}
    else:
        assert tot_charge == {+2, -2}
# --------------------------
@pytest.mark.parametrize('source, target, trigger', _EMULATED)
def test_emulated_samples(
    source  : Component,
    target  : Component,
    trigger : Trigger,
    tmp_path: Path):
    '''
    Test sample emulation, e.g.

    B0 -> Jpsi K* => Bs -> Jpsi K*
    '''
    with RDFGetter.max_entries(value=100_000):
        gtr_1   = RDFGetter(sample=target, trigger=trigger)
        rdf_tar = gtr_1.get_rdf(per_file=False)
        rdf_tar = sel.apply_full_selection(
            rdf      = rdf_tar,
            q2bin    = Qsq.jpsi,
            process  = target,
            trigger  = trigger,
            out_path = tmp_path)

        gtr_2   = RDFGetter(sample=source, trigger=trigger)
        rdf_src = gtr_2.get_rdf(per_file=False)

    log.info(f'Saving validation plots in: {tmp_path}')

    _validate_emulation(
        source = source,
        target = target,
        src    = rdf_src,
        tar    = rdf_tar,
        path   = tmp_path)
# --------------------------
def _validate_emulation(
    source : str,
    target : str,
    src : RDF.RNode,
    tar : RDF.RNode,
    path: Path) -> None:
    for var_name in ['B_M', 'B_Mass', 'q2']:
        arr_src = src.AsNumpy([var_name])[var_name]
        arr_tar = tar.AsNumpy([var_name])[var_name]

        if var_name in ['B_M', 'B_Mass']:
            plt.hist(arr_src, bins=60, range=(5000, 6000), histtype='stepfilled', alpha=0.5, label=source)
            plt.hist(arr_tar, bins=60, range=(5000, 6000), histtype='step', label=target)
        else:
            arr_src = arr_src / 1000_000
            arr_tar = arr_tar / 1000_000

            plt.hist(arr_src, bins=100, range=(0, 22), histtype='stepfilled', alpha=0.5, label=source)
            plt.hist(arr_tar, bins=100, range=(0, 22), histtype='step', label=target)

        nentries = len(arr_src)

        plt.title(f'Entries: {nentries}')
        plt.legend()
        plt.savefig(path / f'{var_name}_linear.png')

        plt.yscale('log')
        plt.savefig(path / f'{var_name}_log.png')
        plt.close()
# ------------------------------------------------
_CUSTOM_PROJECTS=[
    (Component.bpkpee, Trigger.rk_ee_os   ),
    (Component.bpkpee, Trigger.rk_ee_nopid),
]
@pytest.mark.parametrize('component, trigger', _CUSTOM_PROJECTS)
def test_project(component : Component, trigger : Trigger):
    '''
    Will test `project` context manager
    '''
    with RDFGetter.max_entries(value=1000),\
         RDFGetter.project(project=trigger.project):
        gtr = RDFGetter(sample=component, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    nentries = rdf.Count().GetValue()

    assert nentries > 0
# ------------------------------------------------
