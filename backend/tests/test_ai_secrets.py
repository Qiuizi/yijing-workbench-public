from __future__ import annotations

import sys

import pytest

from backend.services.ai_secrets import protect, unprotect


@pytest.mark.skipif(sys.platform != "win32", reason="DPAPI is a Windows user-scoped API")
def test_windows_dpapi_round_trip_does_not_store_plaintext():
    sample = "local-test-key-do-not-use"
    protected = protect(sample)
    assert sample not in protected
    assert unprotect(protected) == sample
