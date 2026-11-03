'''
Module holding tests for Region
'''
import pytest

from pathlib   import Path
from rx_common import Trigger
from rx_common import Brem
from rx_common import Region

# ----------------------------------------
def test_simple():
    brem = Brem.one
    trig = Trigger.rk_ee_os
    rg   = Region(brem = brem, trigger = trig)

    assert rg.name == f'{brem}-{trig.name}'
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
def test_obs(brem : Brem, trigger : Trigger):
    if not trigger.has_pid:
        return

    region      = Region(
        brem    = brem,
        trigger = trigger)

    _ = region.obs
# ----------------------------------------
