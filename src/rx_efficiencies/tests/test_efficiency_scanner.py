'''
Module used to test EfficiencyScanner class
'''

import pytest
import matplotlib.pyplot as plt

from pathlib          import Path
from dmu.workflow     import Cache
from dmu              import LogStore
from rx_common        import Component, Qsq, Trigger, Cuts, Cut, WorkingPoint
from rx_efficiencies  import EfficiencyScanner, EfficiencyScannerConf, EfficiencyGrid

log = LogStore.add_logger('rx_efficiencies:test_efficiency_scanner')
# -----------------------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    LogStore.set_level('rx_efficiencies:efficiency_scanner', 10)
# -----------------------------------
def _plot_values(
    grid    : EfficiencyGrid,
    out_dir : Path) -> None:
    '''
    Plot dataframe as an interpolated mesh
    '''
    df        = grid.df
    df['eff'] = 100 * df['eff']

    pivoted = df.pivot(
            index  ='prc',
            columns='cmb',
            values ='eff')

    v1 : float = pivoted.columns.min() # type: ignore
    v2 : float = pivoted.columns.max() # type: ignore
    v3 : float = pivoted.index.min()
    v4 : float = pivoted.index.max()

    plt.imshow(
        pivoted.values,
        origin='lower',
        extent=(v1, v2, v3, v4),
        cmap='viridis',
        interpolation='bilinear',
    )

    plt.title('Efficiencies vs WP')
    plt.colorbar(label='z')
    plt.xlabel('MVA${}_{comb}$')
    plt.ylabel('MVA${}_{prec}$')
    plt.tight_layout()

    out_path = out_dir / 'efficiencies.png'
    plt.savefig(out_path)
    plt.close()
# -----------------------------------
@pytest.mark.parametrize('sample, q2bin', [
    (Component.bpkpjpsiee , Qsq.jpsi   ),
    (Component.bpkpee     , Qsq.low    ),
    (Component.bpkpee     , Qsq.central),
    (Component.bpkpee     , Qsq.high   )][:1])
def test_scan(sample : Component, q2bin : Qsq, tmp_path : Path):
    '''
    Test efficiency scanning
    '''
    l_wp = [0.50, 0.6, 0.7]
    wps  : list[WorkingPoint] = []
    for cmb in l_wp:
        for prc in l_wp:
            cmb_cut = Cut(
                cut = Cuts.cmb,
                var = 'mva_cmb',
                val = cmb)

            prc_cut = Cut(
                cut = Cuts.prc,
                var = 'mva_prc',
                val = prc)

            wp = WorkingPoint(root = [cmb_cut, prc_cut])

            wps.append(wp)

    cfg  = EfficiencyScannerConf(
        sample   = sample,
        trigger  = Trigger.rk_ee_os,
        q2bin    = q2bin,
        wps      = wps,
    )

    with Cache.cache_root(path = tmp_path):
        obj  = EfficiencyScanner(cfg=cfg)
        grid = obj.run()

    _plot_values(grid = grid, out_dir = tmp_path)
# -----------------------------------
@pytest.mark.parametrize('sample, q2bin', [
    (Component.bpkpjpsiee , Qsq.jpsi   ),
    (Component.bpkpee     , Qsq.low    ),
    (Component.bpkpee     , Qsq.central),
    (Component.bpkpee     , Qsq.high   )][:1])
def test_cache(sample : Component, q2bin : Qsq, tmp_path : Path):
    '''
    Test caching and loading from cache
    '''
    l_wp = [0.50, 0.80]
    wps  : list[WorkingPoint] = []
    for cmb in l_wp:
        for prc in l_wp:
            cmb_cut = Cut(
                cut = Cuts.cmb,
                var = 'mva_cmb',
                val = cmb)

            prc_cut = Cut(
                cut = Cuts.prc,
                var = 'mva_prc',
                val = prc)

            wp = WorkingPoint(root = [cmb_cut, prc_cut])

            wps.append(wp)

    cfg  = EfficiencyScannerConf(
        sample   = sample,
        trigger  = Trigger.rk_ee_os,
        q2bin    = q2bin,
        wps      = wps,
    )

    with Cache.cache_root(path = tmp_path):
        obj    = EfficiencyScanner(cfg=cfg)
        grid_1 = obj.run()

        obj    = EfficiencyScanner(cfg=cfg)
        grid_2 = obj.run()

    assert grid_1 == grid_2
# -----------------------------------
