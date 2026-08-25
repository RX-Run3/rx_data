
import numpy
import numpy.typing as npt

from typing     import Final
from rx_common  import Mass

NpFltArray        = npt.NDArray[numpy.float64]
SIZE : Final[int] = 10_000
# ------------------------------------------------
def get_data() -> dict[str,NpFltArray]:
    rng = numpy.random.default_rng()

    data : dict[str,NpFltArray] = {
        Mass.bp_bcor.value     : rng.uniform(3000, 5100, SIZE),
        Mass.bp_dtf_jpsi.value : rng.normal(loc = 5200, scale = 20, size = SIZE),
        Mass.bp_dtf_psi2.value : rng.normal(loc = 5200, scale = 20, size = SIZE),
    }

    data['B_PT' ]     = rng.poisson(lam = 5_000, size = SIZE).astype(numpy.float64)
    data['block'    ] = rng.integers(low = 1, high = 9, size = SIZE).astype(numpy.float64)
    data['nTracks'  ] = rng.poisson(lam = 3, size = SIZE).astype(numpy.float64)

    data['B_ETA']     = rng.normal(loc = 0.0, scale = 1.0, size = SIZE)
    data['ll_angle' ] = rng.normal(loc = 0.5, scale = 0.1, size = SIZE)
    data['ll_max_PT'] = rng.normal(loc = 20_000, scale = 5_000, size = SIZE)
    data['q2'       ] = rng.uniform(6e6, 22e6, size = SIZE)
    data['q2_dtf'   ] = rng.uniform(6e6, 22e6, size = SIZE)

    return data
# ------------------------------------------------
