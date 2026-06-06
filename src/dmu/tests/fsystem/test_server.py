'''
Module with tests for Server class
'''

from dmu         import LogStore
from dmu.fsystem import Server

log = LogStore.add_logger('dmu:test_server')
# --------------------------------------------
def test_login():
    for elm in Server:
        assert isinstance(elm.login, str)
        log.info(elm.login)
# --------------------------------------------
