
import numpy
import numpy.typing as npt

from typing     import Final
from rx_common  import Channel, Mass

NpFltArray        = npt.NDArray[numpy.float64]
SIZE : Final[int] = 10_000
# ------------------------------------------------
def get_data(channel : Channel) -> dict[str,NpFltArray]:
    rng = numpy.random.default_rng(seed = 42)

    data : dict[str,NpFltArray] = {
        'B_TRUEM'              : rng.uniform(3000, 5100, SIZE),
        'Jpsi_Mass'            : rng.uniform(2500, 3200, SIZE),
        'Jpsi_TRUEM'           : rng.uniform(2500, 3200, SIZE),
        Mass.bp_bcor.value     : rng.normal(loc = 5280, scale = 100,size = SIZE),
        Mass.bp_dtf_jpsi.value : rng.normal(loc = 5200, scale = 20, size = SIZE),
        Mass.bp_dtf_psi2.value : rng.normal(loc = 5200, scale = 20, size = SIZE),
    }

    data['B_PT' ]     = rng.uniform(0, 20_000, size = SIZE).astype(numpy.float64)
    data['block'    ] = rng.integers(low = 1, high = 9, size = SIZE).astype(numpy.float64)
    data['nTracks'  ] = rng.poisson(lam = 3, size = SIZE).astype(numpy.float64)

    if channel == Channel.ee:
        data['nbrem'    ] = rng.integers(low = 1, high = 3, size = SIZE).astype(numpy.float64)
    else:
        data['nbrem'    ] = numpy.zeros(shape = SIZE)

    data['B_ETA']     = rng.normal(loc = 0.0, scale = 1.0, size = SIZE)
    data['ll_angle' ] = rng.normal(loc = 0.5, scale = 0.2, size = SIZE)
    data['ll_max_PT'] = rng.normal(loc = 20_000, scale = 5_000, size = SIZE)
    data['q2'       ] = rng.uniform(6e6, 22e6, size = SIZE)
    data['q2_dtf'   ] = rng.uniform(6e6, 22e6, size = SIZE)

    data['mva.mva_cmb'] = rng.uniform(0, 1, size = SIZE)
    data['mva.mva_prc'] = rng.uniform(0, 1, size = SIZE)

    return data
# ------------------------------------------------
