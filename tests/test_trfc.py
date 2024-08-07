from hqm2.trfc    import trfc 
from zutils.plot  import plot      as zfp

import zutils.utils      as zut
import matplotlib.pyplot as plt
import zfit
import os

#--------------------------------------
class data:
    obs = zfit.Space("B_M", limits=(0, 7000))
#--------------------------------------
def test_simple():
    obj     = trfc(obs=data.obs, qsq_src='psi2', qsq_tgt='high', proc='psi2', dset='2018', pref='test_simple')
    pdf_trf = obj.get_trf()
#--------------------------------------
def main():
    test_simple()
#--------------------------------------
if __name__ == '__main__':
    main()
