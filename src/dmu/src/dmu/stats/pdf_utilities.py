'''
Module with utility functions for PDFs
'''
from typing   import cast
from dmu      import LogStore

from .imports import zfit
from .imports import tensorflow as tf

log=LogStore.add_logger('dmu:pdf_utilities')
# ----------------------
def has_gradient(pdf : zfit.pdf.BasePDF) -> bool:
    '''
    Parameters
    --------------
    pdf: Zfit PDF

    Returns
    --------------
    True if PDF has gradient defined
    '''
    yields = pdf.get_params(is_yield=True) if pdf.is_extended else []

    data   = pdf.sample(n=3).value()
    params = list(pdf.get_params())

    with tf.GradientTape() as tape:
        prob = pdf.pdf(data)

    tensors = cast(list[tf.Variable], params)
    grads   = tape.gradient(
        target = prob,
        sources= tensors)

    missing = False
    for param, gradient in zip(params, grads, strict=True):
        if param in yields:
            continue

        if gradient is None:
            log.warning(f'No gradient for: {param.name}')
            missing = True
        else:
            log.debug(f'Gradient {gradient:g} found for: {param.name}')

    return not missing
# ----------------------
