from hqm2.ratc import ratc

import zfit
import mplhep
import matplotlib.pyplot as plt

from log_store import log_store

#-------------------------------------
class data:
    obs = zfit.Space('B_M', limits=(0, 7000))
#-------------------------------------
def set_logs():
    log_store.set_level('scripts:zutils/utils'    , 30)
    log_store.set_level('rx_hqm2:data_store'      , 30)
    log_store.set_level('rx_scripts:storage/cache', 30)
    log_store.set_level('rx_scripts:atr_mgr:mgr'  , 30)
    log_store.set_level('tools:calc_utility'      , 40)
#-------------------------------------
def test_simple():
    obj=ratc(obs=data.obs, dset='2018')
    rat=obj.get_ratio()
#-------------------------------------
def main():
    log_store.set_level('scripts:zutils/utils', 30)
    plt.style.use(mplhep.style.LHCb2)
    set_logs()

    test_simple()
#-------------------------------------
if __name__ == '__main__': 
    main()

