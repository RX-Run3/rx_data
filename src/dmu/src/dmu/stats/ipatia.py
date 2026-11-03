import zfit
import numpy                  as np
import tensorflow_probability as tfp
import tensorflow             as tf

from dmu.generic             import utilities as gut
from zfit                    import Space, Parameter
from typing                  import Final
from tensorflow.experimental import numpy as tnp

_SQ2PI     : Final[float] = np.sqrt(2.0 * np.arccos(-1.0))
_SQ2PI_INV : Final[float] = 1.0 / _SQ2PI
_LOGSQ2PI  : Final[float] = np.log(_SQ2PI)
_LOG2      : Final[float] = np.log(2.0)

Tensor = tf.Tensor
# -------------------------------------
def _gamma_func(nu : Tensor) -> Tensor:
    '''
    Gamma function
    '''
    log_gamma = tf.math.lgamma(nu)

    return tnp.exp(log_gamma)
# -------------------------------------
def _bessel_second_kind(ni, x) -> Tensor:
    nu          = tnp.abs(ni)
    first_cond  = tf.logical_and(x < 1.0e-06, nu > 0.0)
    second_cond = tf.logical_and(tf.logical_and(x < 1.0e-04, nu > 0.0), nu < 55)
    third_cond  = tf.logical_and(x < 0.1, nu >= 55)
    cond        = tf.logical_or(first_cond, tf.logical_or(second_cond, third_cond))

    low_x_bk    = _gamma_func(nu) * tnp.power(2.0, nu - 1.0) * tnp.power(x, -nu)
    high_x_bk   = tfp.math.bessel_kve(nu, x) * tf.exp(-tf.abs(x))

    return tnp.where(cond, low_x_bk, high_x_bk)
# -------------------------------------
def _log_eval(ax_sigma, lam, rt, beta, pr) -> Tensor:
    dl_ap   = pr * rt
    term_02 = pr ** 2 + ax_sigma ** 2
    term_03 = rt * tnp.sqrt(term_02)

    bes_01  = _bessel_second_kind(lam      ,   dl_ap)
    bes_02  = _bessel_second_kind(lam - 0.5, term_03)

    logno   = lam * tnp.log(rt / pr) - _LOGSQ2PI - tnp.log(bes_01)
    ns1     = 0.5 - lam
    # -------
    term_01 = tnp.log(rt) - 0.5 * tnp.log(term_02)
    tot_log = logno + beta * ax_sigma + ns1 * term_01 + tnp.log(bes_02)

    return tnp.exp(tot_log)
# -------------------------------------
def _diff_eval(d, lam, alpha, beta, delta) -> Tensor:
    gamma   = alpha
    dl_gm   = delta * gamma
    term_02 = delta ** 2 + d ** 2
    term_03 = gamma * tnp.sqrt(term_02)

    bes_01  = _bessel_second_kind(lam      ,   dl_gm)
    bes_02  = _bessel_second_kind(lam + 0.5, term_03)

    no      = tnp.power(gamma / delta, lam) / bes_01 * _SQ2PI_INV
    ns1     = 0.5 - lam
    # -------
    bessel_diff = _bessel_second_kind(lam - 1.5, term_03) +  bes_02
    fact_01     = 2.0 * (beta * term_02 + d * lam) - d
    fact_02     = -d * term_03 * bessel_diff + fact_01 * _bessel_second_kind(ns1, term_03)

    return (
        no
        * tnp.exp(beta * d)
        * tnp.power(gamma, ns1)
        * tnp.power(term_02, lam / 2.0 - 1.25)
        * fact_02
        / 2.0
    )
# -------------------------------------
def _get_tail_n(ax, nx, sigma, lam, rt, beta, pr, diff, sign) -> Tensor: # noqa: PLR0913
    '''
    sign: -1 for left, +1 for right

    Returns
    -------------
    Tensor for tail (right or left) for case when zeta > 0
    '''
    k1    = _log_eval (sign * ax * sigma, lam, rt, beta, pr)
    k2    = _diff_eval(sign * ax * sigma, lam, rt, beta, pr)
    var_b = - ax * sigma - sign * nx * k1 / k2
    var_a = k1 * tnp.power(var_b + ax * sigma,  nx)

    return  var_a * tnp.power(var_b + sign * diff, -nx)
# -------------------------------------
def _get_tail_z(ax, nx, sigma, lam, beta, diff, sign) -> Tensor: # noqa: PLR0913
    '''
    sign: -1 for left, +1 for right

    Returns
    -------------
    Tensor for tail (right or left) for case when zeta == 0
    '''
    cx    = tnp.exp(sign * beta * ax * sigma)
    phx   = 1.0 + ax * ax
    k1    = cx * tnp.power(phx, lam - 0.5)
    k2    = beta  * k1 + sign * cx * (lam - 0.5) * tnp.power(phx, lam - 1.5) * 2 * ax / sigma
    var_b = - ax  * sigma - sign * nx * k1 / k2
    var_a = k1    * tnp.power(var_b + ax * sigma,  nx)

    return var_a * tnp.power(var_b + sign * diff , -nx)
# -------------------------------------
def _get_rat_prd(zeta, lam, sigma) -> tuple[Tensor,Tensor]:
    cons0 = tnp.sqrt(zeta)
    phi   = _bessel_second_kind(lam + 1.0, zeta) / _bessel_second_kind(lam, zeta)
    cons1 = sigma / tnp.sqrt(phi)

    rt    = cons0 / cons1
    pr    = cons0 * cons1

    return rt, pr
# -------------------------------------
@gut.timeit
def _ipatia( # noqa: PLR0913
    x     : Space,
    lam   : Parameter,
    zeta  : Parameter,
    beta  : Parameter,
    mu    : Parameter,
    sigma : Parameter,
    nl    : Parameter,
    nr    : Parameter,
    al    : Parameter,
    ar    : Parameter) -> Tensor:
    rt, pr       = _get_rat_prd(zeta = zeta, lam = lam, sigma = sigma)
    diff         = x - mu

    # zeta > 0
    right_tail_n = _get_tail_n(ar, nr, sigma, lam, rt, beta, pr, diff, +1)
    left_tail_n  = _get_tail_n(al, nl, sigma, lam, rt, beta, pr, diff, -1)

    # zeta = 0
    right_tail_z = _get_tail_z(ar, nr, sigma, lam, beta, diff, +1)
    left_tail_z  = _get_tail_z(al, nl, sigma, lam, beta, diff, -1)

    base         = 1.0 + tnp.power(diff / sigma, 2)
    core_z       = tnp.exp(beta * diff) * tnp.power(base, lam - 0.5)
    core_n       = _log_eval(diff, lam, rt, beta, pr)

    is_left_tail = diff < -al * sigma
    is_right_tail= diff >  ar * sigma

    val_nozero   = tnp.where(is_left_tail, left_tail_n, tnp.where(is_right_tail, right_tail_n, core_n))
    val_yszero   = tnp.where(is_left_tail, left_tail_z, tnp.where(is_right_tail, right_tail_z, core_z))
    val_noneg    = tnp.where(zeta == 0   , val_yszero , val_nozero)

    inv_1 = zeta < 0
    inv_2 = tf.logical_and(zeta == 0, lam >= 0)
    inv   = tf.logical_or(inv_1, inv_2)

    return tnp.where(inv, 0, val_noneg)
# -------------------------------------
class Ipatia(zfit.pdf.ZPDF):
    """Hypatia2 / Ipatia2 PDF (unnormalized). Draft — verify normalization before fitting."""
    _N_OBS  = 1
    _PARAMS = ['mu', 'sigma', 'nl', 'al', 'nr', 'ar', 'lam', 'beta', 'zeta']
    # -------------------
    def _unnormalized_pdf(self, x):
        x     = zfit.z.unstack_x(x)
        mu    = self.params["mu"   ]
        sigma = self.params["sigma"]
        nl    = self.params["nl"   ]
        al    = self.params["al"   ]
        nr    = self.params["nr"   ]
        ar    = self.params["ar"   ]
        lam   = self.params["lam"  ]
        beta  = self.params["beta" ]
        zeta  = self.params["zeta" ]

        res = _ipatia(
            x    = x,
            lam  = lam,
            zeta = zeta,
            beta = beta,
            mu   = mu,
            sigma= sigma,
            nl   = nl,
            nr   = nr,
            al   = al,
            ar   = ar)

        return res
# -------------------------------------
