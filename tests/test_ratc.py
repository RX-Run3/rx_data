from hqm2.ratc import ratc

import zfit

#-------------------------------------
class data:
    obs = zfit.Space('B_M', limits=(0, 7000))
#-------------------------------------
def test_simple():
    obj=ratc(obs=data.obs, dset='2018')
    rat=obj.get_ratio()
#-------------------------------------
def main():
    test_simple()
#-------------------------------------
if __name__ == '__main__': 
    main()

