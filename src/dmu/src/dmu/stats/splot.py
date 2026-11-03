'''
DMU implementation of splot.py module from hepstats.

This is meant to deal locally with:

https://github.com/scikit-hep/hepstats/issues/213
'''

from __future__ import annotations

import warnings
import numpy as np
from zfit import Parameter

from dmu.stats                    import zfit
from typing                       import Any, Final, cast
from hepstats.utils               import eval_pdf
from hepstats.utils.fit.api_check import is_valid_pdf
from hepstats.splot.exceptions    import ModelNotFittedToData
from hepstats.splot.warnings      import AboveToleranceWarning

_ATOL_WARNING       : Final[float] = 5e-3 # If the 'mlsr' is below this value, it will show a warning
_MIN_YIELD_FRACTION : Final[float] = 1e-2 # Components with less than this fraction
                                          # of the data will be considered small
# --------------------------------------------------------------------------------
def is_sum_of_extended_pdfs(model) -> bool:
    """Checks if the input model is a sum of extended models.

    Args:
         model: the input model/pdf

    Returns:
         True if the model is a sum of extended models, False if not.
    """
    if not hasattr(model, "get_models"):
        return False

    return all(m.is_extended for m in model.get_models()) and model.is_extended
# --------------------------------------------------------------------------------
def compute_sweights(
    model : zfit.pdf.SumPDF,
    x: np.ndarray,
    *,
    atol_exceptions: float = 5e-2) -> dict[Any, np.ndarray]:
    """Computes sWeights from probability density functions for different components/species in a fit model
    (for instance signal and background) fitted on some data `x`.

    i.e. model = Nsig * pdf_signal + Nbkg * pdf_bkg

    Args:
        model: sum of extended pdfs.
        x: data on which `model` is fitted
        atol_exceptions: absolute tolerance to check if the Maximum Likelihood Sum Rule sanity check,
            described in equation 17 of arXiv:physics/0402083, failed. Sum of yields should be 1 with
            an absolute tolerance of `atol_exceptions`.

    Returns:
        dictionary with yield parameters as keys, and sWeights for correspoind species as values.

    Example with **zfit**:

        Imports:

        >>> import numpy as np
        >>> import zfit
        >>> from zfit.loss import ExtendedUnbinnedNLL
        >>> from zfit.minimize import Minuit

        Definition of the bounds and yield of background and signal species:

        >>> bounds = (0.0, 3.0)
        >>> nbkg = 10000
        >>> nsig = 5000
        >>> obs = zfit.Space('x', limits=bounds)

        Generation of data:

        >>> bkg = np.random.exponential(0.5, nbkg)
        >>> peak = np.random.normal(1.2, 0.1, nsig)
        >>> data = np.concatenate((bkg, peak))
        >>> data = data[(data > bounds[0]) & (data < bounds[1])]
        >>> N = data.size
        >>> data = zfit.data.Data.from_numpy(obs=obs, array=data)

        Model definition:

        >>> mean = zfit.Parameter("mean", 1.2, 0.5, 2.0)
        >>> sigma = zfit.Parameter("sigma", 0.1, 0.02, 0.2)
        >>> lambda_ = zfit.Parameter("lambda", -2.0, -4.0, -1.0)
        >>> Nsig = zfit.Parameter("Nsig", nsig, 0., N)
        >>> Nbkg = zfit.Parameter("Nbkg", nbkg, 0., N)
        >>> signal = zfit.pdf.Gauss(obs=obs, mu=mean, sigma=sigma).create_extended(Nsig)
        >>> background = zfit.pdf.Exponential(obs=obs, lambda_=lambda_).create_extended(Nbkg)
        >>> tot_model = zfit.pdf.SumPDF([signal, background])

        Loss construction and minimization:

        >>> loss = ExtendedUnbinnedNLL(model=signal + background, data=data)
        >>> minimizer = Minuit()
        >>> minimum = minimizer.minimize(loss)

        sWeights computation:

        >>> from hepstats.splot import compute_sweights
        >>> sweights = compute_sweights(tot_model, data)
        >>> print(sweights)
        {<zfit.Parameter 'Nsig' floating=True value=4985>: array([-0.09953299, -0.09953299, -0.09953299, ...,
        0.78689884, 1.08823111,  1.05948873]),
        <zfit.Parameter 'Nbkg' floating=True value=9989>: array([ 1.09953348,  1.09953348,  1.09953348, ...,
        0.21310097, -0.08823153, -0.05948912])}
    """

    if not is_valid_pdf(model):
        msg = f"{model} is not a valid pdf!"
        raise ValueError(msg)

    if not is_sum_of_extended_pdfs(model):
        msg = f"Input model, {model}, should be a sum of extended pdfs!"
        raise ValueError(msg)

    full_yield = model.get_yield()
    if full_yield == 0:
        raise ValueError('Full model yield is zero')

    if full_yield is None:
        raise ValueError('Cannot find full model yield')

    models     = model.get_models()
    yields     = [ m.get_yield()                                               for               m in models ]
    if any(component_yield is None for component_yield in yields):
        raise ValueError('At least one component yield was not found')
    else:
        yields = cast(list[Parameter], yields)

    not_small  = np.array([ component_yield / full_yield > _MIN_YIELD_FRACTION for component_yield in yields ])

    p  = np.vstack([eval_pdf(m, x) for m in models]).T
    Nx = eval_pdf(model, x, allow_extended=True)
    pN = p / Nx[:, None]

    mlsr = pN.sum(axis=0)
    def msg_fn(tolerance):
        msg = (
            "The Maximum Likelihood Sum Rule sanity check, described in equation 17 of"
            + " arXiv:physics/0402083, failed. According to this check the following quantities\n"
        )
        for yield_var, component_mlsr in zip(yields, mlsr, strict=True):
            msg += f"\t* {yield_var.name}: {component_mlsr},\n"
        msg += f"should be equal to 1.0 with an absolute tolerance of {tolerance}."
        return msg

    # Do not apply check to small components
    # These tend to fail check and make code fragile
    mlsr_not_small = mlsr[not_small]

    if not np.allclose(mlsr_not_small, 1, atol=atol_exceptions):
        msg = msg_fn(atol_exceptions)
        msg += " The numbers suggest that the model is not fitted to the data. Please check your fit."
        raise ModelNotFittedToData(msg)

    if not np.allclose(mlsr_not_small, 1, atol=_ATOL_WARNING):
        msg = msg_fn(_ATOL_WARNING)
        msg += " If the fit to the data is good please ignore this warning."
        warnings.warn(msg, AboveToleranceWarning, stacklevel=2)

    Vinv = (pN).T.dot(pN)
    V = np.linalg.inv(Vinv)

    sweights = p.dot(V) / Nx[:, None]

    return {y: sweights[:, i] for i, y in enumerate(yields)}
