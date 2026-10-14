'''
Module holding tests for Region
'''
import pytest

from pathlib   import Path
from rx_common import Particle
from rx_common import Trigger
from rx_common import Brem
from rx_common import Region

# ----------------------------------------
def test_simple():
    brem = Brem.one
    trig = Trigger.rk_ee_os

    rg1  = Region(brem = brem)
    rg2  = Region(brem = brem, trigger = trig)

    assert rg1.name == str(brem)
    assert rg2.name == f'{brem}-{trig.name}' 
# ----------------------------------------
def test_serialize(tmp_path : Path):
    brem = Brem.one
    trig = Trigger.rk_ee_os
    rg1  = Region(brem = brem, trigger = trig)

    path = tmp_path / 'region.json'

    rg1.to_json(path = path)

    rg2 = Region.from_json(path = path)

    assert rg2 == rg1
# ----------------------------------------
@pytest.mark.parametrize("brem", Brem)
@pytest.mark.parametrize("trigger", Trigger)
@pytest.mark.parametrize("lepton", [Particle.kaon, Particle.pion])
def test_obs(brem : Brem, trigger : Trigger, lepton : Particle):
    region = Region(brem=brem, trigger=trigger, lepton=lepton)
    _ = region.obs
# ----------------------------------------
