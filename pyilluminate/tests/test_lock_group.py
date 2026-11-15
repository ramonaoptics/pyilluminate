import os

import pytest

from pyilluminate import illuminate


@pytest.mark.skipif(os.name == 'nt', reason='no unix groups')
def test_lock_without_group_membership(tmp_path, monkeypatch):
    if os.geteuid() == 0:
        pytest.skip('root is in every group')
    monkeypatch.setattr(illuminate, 'locks_dir', tmp_path / 'locks')
    lock = illuminate.Illuminate._make_lock('X', group='root')
    lock.acquire()
    lock.release()
    other = illuminate.Illuminate._make_lock('X', group='root')
    lock.acquire()
    other.timeout = 0
    with pytest.raises(illuminate.Timeout):
        other.acquire()
    lock.release()
