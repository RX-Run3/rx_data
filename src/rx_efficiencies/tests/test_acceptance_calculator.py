'''
Module meant to test the AcceptanceCalculator class
'''

import os

import pytest
import mplhep
import matplotlib.pyplot as plt

from pathlib         import Path
from ROOT            import RDataFrame
from dmu             import LogStore
from dmu.generic     import version_management    as vmn
from dmu.generic     import rxran
from rx_efficiencies import AcceptanceCalculator
from rx_common       import Channel
from rx_common       import Project 
from rx_common       import Component 

log=LogStore.add_logger('rx_efficiencies:test_acceptance_calculator')

_BACKGROUNDS = [
    (Component.bsphiee       , Channel.ee, Project.rk),
    (Component.bpkstkpiee    , Channel.ee, Project.rk),
    # ------
    (Component.bpk1kpipiee   , Channel.ee, Project.rk),
    (Component.bpk2kpipiee   , Channel.ee, Project.rk),
    # ------
    (Component.bpk1kpipiee   , Channel.ee, Project.rkst),
    (Component.bpk2kpipiee   , Channel.ee, Project.rkst),
]

_SIGNALS = [
    (Component.bpkpee        , Channel.ee, Project.rk),
    (Component.bpkpmm        , Channel.mm, Project.rk),
    # ---
    (Component.bpkpjpsiee    , Channel.ee, Project.rk),
    (Component.bpkpjpsimm    , Channel.mm, Project.rk),
    # ---
    (Component.bpkppsi2ee    , Channel.ee, Project.rk),
    (Component.bpkppsi2mm    , Channel.mm, Project.rk),
    # ---
    # ---
    (Component.bdkstkpiee    , Channel.ee, Project.rk),
    (Component.bdkstkpimm    , Channel.mm, Project.rk),
    # ---
    (Component.bdkstkpijpsiee, Channel.ee, Project.rk),
    (Component.bdkstkpijpsimm, Channel.mm, Project.rk),
    # ---
    (Component.bdkstkpipsi2ee, Channel.ee, Project.rk),
    (Component.bdkstkpipsi2mm, Channel.mm, Project.rk),
    # ---
    # ---
    (Component.bdkstkpiee    , Channel.ee, Project.rkst),
    (Component.bdkstkpimm    , Channel.mm, Project.rkst),
    # ---
    (Component.bdkstkpijpsiee, Channel.ee, Project.rkst),
    (Component.bdkstkpijpsimm, Channel.mm, Project.rkst),
    # ---
    (Component.bdkstkpipsi2ee, Channel.ee, Project.rkst),
    (Component.bdkstkpipsi2mm, Channel.mm, Project.rkst),
]
#--------------------------
class Data:
    '''
    Data class
    '''
    rsm_dir : Path 

    plt.style.use(mplhep.style.LHCb2)
#--------------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This runs before any test
    '''
    LogStore.set_level('rx_efficiencies:test_acceptance_calculator', 10)

    ana_dir      = Path(os.environ['ANADIR'])
    Data.rsm_dir = vmn.get_last_version(dir_path=ana_dir / 'Rapidsim', version_only=False)

    with rxran.seed(value = 42):
        yield
#--------------------------
def _get_rdf(sample : str, energy : str) -> RDataFrame:
    file_path = f'{Data.rsm_dir}/{sample}/{energy}/{sample}_tree.root'
    rdf       = RDataFrame('DecayTree', file_path)

    return rdf
#--------------------------
@pytest.mark.parametrize('energy', ['8TeV', '13TeV', '14TeV'])
@pytest.mark.parametrize('sample, channel, project', _SIGNALS + _BACKGROUNDS)
def test_sample(
    energy   : str, 
    sample   : Component, 
    channel  : Channel,
    project  : Project,
    tmp_path : Path):
    '''
    Simplest test of geometric acceptance calculation for different samples
    '''
    rdf = _get_rdf(sample=sample.name, energy=energy)
    obj = AcceptanceCalculator(
        rdf    = rdf, 
        channel= channel, 
        project= project)

    obj.plot_dir     = tmp_path / f'{sample.name}/{energy}'
    acc_phy, acc_lhc = obj.get_acceptances()

    log.info(f'{sample:<20}{acc_phy:10.3f}{acc_lhc:10.3f}')

    assert acc_phy >= acc_lhc
#--------------------------
