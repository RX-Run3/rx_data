'''
Module with tests for PdfBuilder class
'''
from contextlib     import ExitStack
from dmu.stats      import print_pdf
from dmu.workflow   import Cache
from pathlib        import Path
from rx_common      import Component, Qsq, Trigger, Cuts
from hqm.data_store import DataStore
from hqm.pdf_mc     import PdfBuilder

def test_simple(tmp_path : Path):
    '''
    Simplest test
    '''
    sel             = {}
    sel[Cuts.q2   ] = '(q2_dtf > 11e6) & (q2_dtf < 15e6)'
    sel[Cuts.block] = 'block == 1'

    ctx1 = Cache.cache_root(path = tmp_path)
    ctx2 = DataStore.selection(sel = sel)

    with ExitStack() as stack:
        stack.enter_context(ctx1)
        stack.enter_context(ctx2)

        obj = PdfBuilder(
            comp    = Component.bpkppsi2ee,
            trigger = Trigger.rk_ee_os,
            qsq     = Qsq.psi2)

        pdf = obj.get_pdf()

        print_pdf(pdf = pdf)
