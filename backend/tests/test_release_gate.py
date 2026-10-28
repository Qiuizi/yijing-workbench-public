"""正式发布公钥门禁：仓库公钥、环境公钥、QA 公钥三者必须一致地拒绝/放行。"""

import base64

import pytest

from scripts.updater import keys, release_gate


def make_key(seed: int) -> str:
    """构造一个结构合法的 minisign 公钥（不是真实密钥，只用于格式判断）。"""
    key_id = bytes([seed] * 8)
    payload = b"Ed" + key_id + bytes([seed] * 32)
    text = (
        "untrusted comment: minisign public key: TEST\n"
        + base64.b64encode(payload).decode()
        + "\n"
    )
    return base64.b64encode(text.encode()).decode()


PROD_KEY = make_key(0x11)
OTHER_KEY = make_key(0x22)


@pytest.fixture
def repo_with_key(monkeypatch):
    """把「仓库内置公钥」和「版本一致性」替换成受控值。"""
    state = {"key": PROD_KEY}

    monkeypatch.setattr(release_gate, "app_public_key", lambda root: state["key"])
    monkeypatch.setattr(release_gate, "assert_versions_consistent", lambda root, expected=None: "3.3.2")
    return state


def test_production_key_and_matching_env_key_pass(repo_with_key):
    ok, message = release_gate.check("3.3.2", PROD_KEY)
    assert ok is True
    assert "key_id" in message
    assert keys.is_qa_key(PROD_KEY) is False


def test_qa_key_in_repo_is_always_rejected(repo_with_key):
    repo_with_key["key"] = keys.QA_PUBLIC_KEY
    ok, message = release_gate.check("3.3.2", keys.QA_PUBLIC_KEY)
    assert ok is False
    assert "QA" in message


def test_qa_key_in_environment_is_rejected(repo_with_key):
    ok, message = release_gate.check("3.3.2", keys.QA_PUBLIC_KEY)
    assert ok is False


def test_repo_key_and_env_key_mismatch_is_rejected(repo_with_key):
    ok, message = release_gate.check("3.3.2", OTHER_KEY)
    assert ok is False
    assert "不一致" in message


def test_invalid_env_key_is_rejected(repo_with_key):
    ok, message = release_gate.check("3.3.2", "not-a-key")
    assert ok is False
    assert "不是有效的 minisign 公钥" in message


def test_absent_env_key_keeps_legacy_behaviour(repo_with_key):
    ok, _ = release_gate.check("3.3.2", None)
    assert ok is True


def test_qa_fingerprint_and_key_id_are_stable():
    """QA 公钥的 key id / 指纹必须稳定，便于在文档与日志里引用。"""
    from scripts.updater import manifest

    assert manifest.public_key_key_id(keys.QA_PUBLIC_KEY) == "7B072FC9CF8B402F"
    assert manifest.public_key_fingerprint(keys.QA_PUBLIC_KEY) == "093E59E9B93FE19E"
