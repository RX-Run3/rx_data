
import zfit
import mplhep
import matplotlib.pyplot as plt

from hqm.ratc import CCbarRatioCalculator
from dmu      import LogStore
#-------------------------------------
class data:
    obs = zfit.Space('B_M', limits=(0, 7000))
#-------------------------------------
def set_logs():
    LogStore.set_level('scripts:zutils/utils'    , 30)
    LogStore.set_level('rx_hqm2:data_store'      , 30)
    LogStore.set_level('rx_scripts:storage/cache', 30)
    LogStore.set_level('rx_scripts:atr_mgr:mgr'  , 30)
    LogStore.set_level('tools:calc_utility'      , 40)
#-------------------------------------
def test_proc(proc):
    obj=CCbarRatioCalculator(obs=data.obs, dset='2018', proc=proc)
    rat=obj.get_ratio()
#-------------------------------------
def main():
    log_store.set_level('scripts:zutils/utils', 30)
    plt.style.use(mplhep.style.LHCb2)
    set_logs()

    test_proc('psi2')
    test_proc('ctrl')
#-------------------------------------
if __name__ == '__main__': 
    main()

