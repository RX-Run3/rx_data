'''
Module with tests for ParameterLibrary class
'''
import pytest

from dmu            import LogStore
from dmu.stats      import zfit
from dmu.stats      import Model
from dmu.stats      import YieldsConf
from dmu.stats      import ParameterLibrary as PL
from dmu.generic    import utilities        as gut
from zfit.param     import Parameter, ComposedParameter

log=LogStore.add_logger('dmu:test_parameter_library')

type zpar = Parameter | ComposedParameter
# ----------------------
@pytest.fixture(scope='module', autouse=True)
def initialize():
    '''
    This runs before the tests
    '''
    LogStore.set_level('dmu:stats:parameters', 10)
# ----------------------
def _check_parameter(par : zpar) -> None:
    '''
    Parameters
    -------------
    par: Zfit parameter
    '''
    if not isinstance(par, (zfit.Parameter, zfit.ComposedParameter)):
        type_name = type(par)
        raise TypeError(f'Object is not a parameter but: {type_name}')

    log.info(par)

    val = par.value().numpy() # type: ignore
    assert isinstance(val, float)

    if 'BdKstee' in par.name:
        assert _composed_has_par(name='s_BdKstee', par=par)

    if 'BuKstee' in par.name:
        assert _composed_has_par(name='s_BuKstee', par=par)
# ----------------------
def _composed_has_par(name : str, par : zpar) -> bool:
    '''
    Parameters
    -------------
    name: Name of the component parameter to find
    par : Composed parameter

    Returns
    -------------
    True if `name` parameter exists in `par`
    '''
    s_flt = par.get_params(floating= True)
    s_fix = par.get_params(floating=False)

    s_all = s_flt | s_fix

    for sub_par in s_all:
        if sub_par.name == name:
            return True

    return False
# ------------------------------------
@pytest.mark.parametrize('model', Model)
def test_print(model : Model):
    '''
    Will test printing parameters
    '''
    PL.print_parameters(kind=model)
# ------------------------------------
def test_get_values():
    '''
    Will test retrieving values for different parameters of cbl
    '''
    kind = Model.cbl

    for par in ['mu', 'sg', 'al', 'nl']:
        x, y, z = PL.get_values(kind=kind, parameter=par)

        log.info(f'{par:<20}{x:<10.0f}{y:<10.0f}{z:<10.0f}')
# ------------------------------------
@pytest.mark.parametrize('parameter', ['mu', 'sg', 'al', 'nl'])
def test_values(parameter : str):
    '''
    Will test retrieving values for different parameters of cbl
    '''
    kind = Model.cbl
    v_in = 22222
    l_in = 11111
    h_in = 33333

    with PL.values(kind=kind, parameter=parameter, val=v_in, low=l_in, high=h_in):
        v_out, l_out, h_out = PL.get_values(kind=kind, parameter=parameter)

    assert v_in == v_out
    assert l_in == l_out
    assert h_in == h_out

    v_out, l_out, h_out = PL.get_values(kind=kind, parameter=parameter)

    assert v_in != v_out
    assert l_in != l_out
    assert h_in != h_out
# ------------------------------------
@pytest.mark.parametrize('config', ['scales', 'simultaneous'])
def test_get_yield(config : str) -> None:
    '''
    Tests get_yield method
    '''
    data = gut.load_data(package='dmu_data', fpath=f'tests/stats/parameters/{config}.yaml')
    cfg  = YieldsConf(**data)

    pars = dict()
    with PL.parameter_schema(cfg=cfg):
        for parname, _ in cfg:
            par           = PL.get_yield(name=parname)
            pars[parname] = par

            _check_parameter(par=par)

    if config == 'simultaneous':
        assert pars['yield_001'] is pars['yield_003']
# ------------------------------------
