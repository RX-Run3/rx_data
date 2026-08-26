'''
Module with tests for PdfBuilder class
'''
from contextlib import ExitStack

from dmu.workflow import Cache
from pathlib      import Path
from rx_common    import Component, Qsq, Trigger, Cuts
from rx_selection import selection as sel
from hqm.pdf_mc   import PdfBuilder

def test_simple(tmp_path : Path):
    '''
    Simplest test
    '''
    ctx1 = Cache.cache_root(path = tmp_path)
    ctx2 = sel.custom_selection(d_sel = {Cuts.block : '1'})

    with ExitStack() as stack:
        stack.enter_context(ctx1)
        stack.enter_context(ctx2)

        obj = PdfBuilder(
            comp    = Component.bpkppsi2ee,
            trigger = Trigger.rk_ee_os,
            qsq     = Qsq.psi2)

        pdf = obj.get_pdf()
