'''
Module intended to provide access to other projects when they cannot be accessed directly

- Tensorflow and zfit: zfit uses tensorflow and tensorflow will cause a crash when imported before ROOT
'''
try:
    import ROOT  # noqa: F401
except ImportError:
    pass

import dmu.generic.utilities as gut
with gut.silent_import():
    import tensorflow # noqa: F401
    from tensorflow import config as tf_config # noqa: F401

import zfit  # noqa: F401
