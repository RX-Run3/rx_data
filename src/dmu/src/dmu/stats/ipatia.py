"""
Draft implementation of the Ipatia2 (Hypatia2) PDF for zfit.

Source: https://gist.github.com/jonas-eschle/e829f6c85181c6bc30f8d69dd0b6d963
Author: jonas-eschle (zfit core maintainer), created 2022-08-08

Reference distribution: RooHypatia2 in ROOT/RooFit
https://root.cern.ch/doc/master/classRooHypatia2.html
Based on: https://arxiv.org/abs/1312.5000

NOTE: this is an unofficial draft, not part of zfit or zfit-physics.
Needs testing / normalization checks before production use.
"""

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

    return tnp.where(cond, low_x_bk, tfp.math.bessel_kve(nu, x))
# -------------------------------------
def _log_eval(d, lam, alpha, beta, delta) -> Tensor:
    gamma   = alpha
    dl_gm   = delta * gamma
    term_02 = delta ** 2 + d ** 2
    term_03 = gamma * tnp.sqrt(term_02)

    bes_01  = _bessel_second_kind(lam      ,   dl_gm)
    bes_02  = _bessel_second_kind(lam - 0.5, term_03)

    logno   = lam * tnp.log(gamma / delta) - _LOGSQ2PI - tnp.log(bes_01)
    ns1     = 0.5 - lam
    # -------
    term_01 = tnp.log(gamma) - 0.5 * tnp.log(term_02)
    tot_log = logno + beta * d + ns1 * term_01 + tnp.log(bes_02)

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
@gut.timeit
def _ipatia(
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
    diff    = x - mu
    cons0   = tnp.sqrt(zeta)
    asigma  = al * sigma
    a2sigma = ar * sigma

    cond1   = diff < -asigma
    cond2   = diff > a2sigma

    phi   = _bessel_second_kind(lam + 1.0, zeta) / _bessel_second_kind(lam, zeta)
    cons1 = sigma / tnp.sqrt(phi)
    alpha = cons0 / cons1
    delta = cons0 * cons1

    k1    = _log_eval (-asigma, lam, alpha, beta, delta)
    k2    = _diff_eval(-asigma, lam, alpha, beta, delta)
    var_b = -asigma + nl * k1 / k2
    var_a = k1    * tnp.power(var_b + asigma,  nl)
    out1  = var_a * tnp.power(var_b - diff  , -nl)

    k1    = _log_eval( a2sigma, lam, alpha, beta, delta)
    k2    = _diff_eval(a2sigma, lam, alpha, beta, delta)
    var_b = -a2sigma - nr * k1 / k2
    var_a = k1    * tnp.power(var_b + a2sigma,  nr)
    out2  = var_a * tnp.power(var_b + diff   , -nr)

    out3  = _log_eval(diff, lam, alpha, beta, delta)

    cons1 = -2.0 * lam
    condx = lam <= -1.0

    delta1= sigma * tnp.sqrt(-2 + cons1)
    delta = tnp.where(condx, delta1, sigma)
    delta2= delta * delta

    cons1 = tnp.exp(-beta * asigma)
    phi   = 1.0 + asigma * asigma / delta2
    k1    = cons1 * tnp.power(phi, lam - 0.5)
    k2    = beta  * k1 - cons1 * (lam - 0.5) * tnp.power(phi, lam - 1.5) * 2 * asigma / delta2
    var_b = -asigma + nl * k1 / k2
    var_a = k1    * tnp.power(var_b + asigma,  nl)
    outz1 = var_a * tnp.power(var_b - diff  , -nl)

    cons1 = tnp.exp(beta * a2sigma)
    phi   = 1.0 + a2sigma * a2sigma / delta2
    k1    = cons1 * tnp.power(phi, lam - 0.5)
    k2    = beta * k1 + cons1 * (lam - 0.5) * tnp.power(phi, lam - 1.5) * 2.0 * a2sigma / delta2
    var_b = -a2sigma - nr * k1 / k2
    var_a = k1    * tnp.power(var_b + a2sigma,  nr)
    outz2 = var_a * tnp.power(var_b + diff   , -nr)

    outz3 = tnp.exp(beta * diff) * tnp.power(1.0 + diff * diff / delta2, lam - 0.5)

    val_nozero = tnp.where(cond1, out1 , tnp.where(cond2, out2 , out3 ))
    val_yszero = tnp.where(cond1, outz1, tnp.where(cond2, outz2, outz3))

    return tnp.where(zeta != 0, val_nozero, val_yszero)
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
