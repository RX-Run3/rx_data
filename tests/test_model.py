from hqm.model import get_part_reco
from hqm.model import get_Bu2Ksee_shape
from hqm.model import get_Bd2Ksee_shape
from hqm.model import get_signal_shape
from hqm.model import get_Bs2phiee_shape
from hqm.model import get_Bu2K1ee_shape
from hqm.model import get_Bu2K2ee_shape


Bd2Ksee_shape  = get_Bd2Ksee_shape(dataset="2018", trigger="ETOS", parameter_name_prefix="prefix", bts_index=0)
Bu2Ksee_shape  = get_Bu2Ksee_shape(dataset="2018", trigger="ETOS", parameter_name_prefix="prefix", bts_index=0)
Bs2phiee_shape = get_Bs2phiee_shape(dataset="2018", trigger="ETOS", parameter_name_prefix="prefix", bts_index=0)
Bu2K1ee_shape  = get_Bu2K1ee_shape(dataset="2018", trigger="ETOS", parameter_name_prefix="prefix", bts_index=0)
Bu2K2ee_shape  = get_Bu2K2ee_shape(dataset="2018", trigger="ETOS", parameter_name_prefix="prefix", bts_index=0)

#resonant part-reco + psi2S K & ratio constraint
part_reco_shape, constraints = get_part_reco(dataset="2018", trigger="ETOS", parameter_name_prefix="prefix", systematic="nom", bts_index=0)
def test_signal
signal_shape_mm, constraints = get_signal_shape(dataset="2018", trigger="MTOS", parameter_name_prefix="prefix", systematic="nom")
signal_shape_ee, constraints = get_signal_shape(dataset="2018", trigger="ETOS", parameter_name_prefix="prefix", systematic="nom")

