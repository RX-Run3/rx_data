from hqm2.ratc import ratc

import zfit
import mplhep
import matplotlib.pyplot as plt

from log_store import log_store

#-------------------------------------
class data:
    obs = zfit.Space('B_M', limits=(0, 7000))
#-------------------------------------
def test_simple():
    obj=ratc(obs=data.obs, dset='2018')
    rat=obj.get_ratio()
#-------------------------------------
def main():
    log_store.set_level('scripts:zutils/utils', 30)
    plt.style.use(mplhep.style.LHCb2)

    test_simple()
#-------------------------------------
if __name__ == '__main__': 
    main()

