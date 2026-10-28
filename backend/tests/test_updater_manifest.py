"""更新清单与发布契约的单元测试（不涉及真实签名私钥）。"""

import base64
import base64
import json
import re
from pathlib import Path

import pytest

from scripts.updater import manifest
from scripts.updater.keys import QA_PUBLIC_KEY, app_public_key, describe_public_key, is_qa_key
from scripts.updater.update_site_release import apply_to_source

REPO_ROOT = Path(__file__).resolve().parents[2]
# Tauri 的 .sig 是「整份 minisign 文件」的 base64，不是明文多行文本。
# 这里构造一对「key id 自洽」的假密钥/假签名：结构合法、密码学上不合法，
# 足以驱动 manifest/contract 的格式与一致性校验（真实验签见 Rust 校验器）。
_FAKE_KEY_ID = bytes.fromhex("1122334455667788")


def _fake_public_key_b64() -> str:
    payload = b"Ed" + _FAKE_KEY_ID + bytes(range(32))
    text = "untrusted comment: minisign public key: TEST\n" + base64.b64encode(payload).decode() + "\n"
    return base64.b64encode(text.encode()).decode()


FAKE_PUBKEY = _fake_public_key_b64()


def _fake_signature_text(key_id: bytes = _FAKE_KEY_ID) -> str:
    sig_line = base64.b64encode(b"Ed" + key_id + bytes(64)).decode()
    global_line = base64.b64encode(b"Ed" + key_id + bytes(64)).decode()
    return (
        "untrusted comment: signature from tauri secret key\n"
        f"{sig_line}\n"
        "trusted comment: timestamp:1793081026\tfile:test-setup.exe\n"
        f"{global_line}\n"
    )


_MINISIGN_TEXT = _fake_signature_text()
SIGNATURE = base64.b64encode(_MINISIGN_TEXT.encode("utf-8")).decode("ascii")


def _fake_bundle(tmp_path: Path, version: str = "3.3.2", *, with_signature: bool = True) -> Path:
    bundle = tmp_path / "nsis"
    bundle.mkdir()
    # 模拟 Tauri 的原始产物命名（productName 是中文），发布时再重命名为规范名
    installer = bundle / f"易经起卦工作台_{version}_x64-setup.exe"
    installer.write_bytes(b"fake-installer-bytes" * 32)
    if with_signature:
        installer.with_name(installer.name + ".sig").write_text(SIGNATURE, encoding="utf-8")
    return bundle


def _build_release(tmp_path: Path, version: str = "3.3.2", tag: str = "v3.3.2") -> Path:
    from scripts.updater.build_release_dir import main as build_main

    bundle = _fake_bundle(tmp_path, version)
    out = tmp_path / "release"
    assert build_main([
        "--bundle-dir", str(bundle),
        "--out", str(out),
        "--tag", tag,
        "--version", version,
        "--notes", "测试更新说明",
        "--source-sha", "deadbeef" * 5,
        "--updater-pubkey", FAKE_PUBKEY,
    ]) == 0
    return out


def test_latest_json_roundtrip_has_required_fields(tmp_path):
    release = _build_release(tmp_path)
    data = json.loads((release / "latest.json").read_text(encoding="utf-8"))
    for key in ("version", "notes", "pub_date", "platforms"):
        assert key in data
    entry = data["platforms"]["windows-x86_64"]
    assert entry["url"].startswith("https://github.com/Qiuizi/yijing-workbench-public/releases/download/v3.3.2/")
    assert entry["url"].endswith("yijing-workbench-3.3.2-x64-setup.exe")
    assert (release / "yijing-workbench-3.3.2-x64-setup.exe").exists()
    assert (release / "yijing-workbench-3.3.2-x64-setup.exe.sig").exists()
    build_manifest = json.loads((release / "manifest.json").read_text(encoding="utf-8"))
    assert build_manifest["installer"]["original_filename"].startswith("易经起卦工作台_3.3.2")
    assert entry["signature"] == SIGNATURE.strip()
    assert manifest.validate_latest_json(data, expected_version="3.3.2", repo="Qiuizi/yijing-workbench-public", tag="v3.3.2") == []


def test_release_dir_passes_verification(tmp_path):
    from scripts.updater.verify_release import verify

    release = _build_release(tmp_path)
    assert verify(release, tag="v3.3.2", repo="Qiuizi/yijing-workbench-public", production=False, expected_version="3.3.2") == []


def test_tampered_installer_is_rejected(tmp_path):
    from scripts.updater.verify_release import verify

    release = _build_release(tmp_path)
    installer = next(release.glob("*setup.exe"))
    installer.write_bytes(installer.read_bytes() + b"tampered")

    problems = verify(release, tag="v3.3.2", repo="Qiuizi/yijing-workbench-public", production=False, expected_version="3.3.2")
    assert any("哈希不一致" in item for item in problems)
    assert any("字节数不一致" in item for item in problems)


def test_missing_signature_is_rejected(tmp_path):
    bundle = _fake_bundle(tmp_path, with_signature=False)
    with pytest.raises(manifest.UpdaterManifestError) as error:
        manifest.collect_bundle(bundle, "3.3.2")
    assert "缺少签名文件" in str(error.value)


def test_latest_json_without_signature_is_rejected():
    with pytest.raises(manifest.UpdaterManifestError) as error:
        manifest.build_latest_json(
            version="3.3.2", notes="x", asset_name="a-3.3.2-x64-setup.exe", signature="  ",
            repo="Qiuizi/yijing-workbench-public", tag="v3.3.2",
        )
    assert "缺少更新包签名" in str(error.value)


def test_plain_multiline_signature_is_rejected():
    """回归：把 minisign 明文直接塞进 signature 字段（而不是 base64）必须被拒绝。"""
    data = {
        "version": "3.3.2",
        "notes": "x",
        "pub_date": "2026-10-27T00:00:00Z",
        "platforms": {"windows-x86_64": {
            "signature": _MINISIGN_TEXT,
            "url": "https://github.com/Qiuizi/yijing-workbench-public/releases/download/v3.3.2/yijing-workbench-3.3.2-x64-setup.exe",
        }},
    }
    errors = manifest.validate_latest_json(data)
    assert any("不是有效的签名内容" in item for item in errors)


def test_plain_multiline_signature_is_rejected():
    """回归：把 minisign 明文直接塞进 signature 字段（而不是 base64）必须被拒绝。"""
    data = {
        "version": "3.3.2",
        "notes": "x",
        "pub_date": "2026-10-27T00:00:00Z",
        "platforms": {"windows-x86_64": {
            "signature": _MINISIGN_TEXT,
            "url": "https://github.com/Qiuizi/yijing-workbench-public/releases/download/v3.3.2/yijing-workbench-3.3.2-x64-setup.exe",
        }},
    }
    errors = manifest.validate_latest_json(data)
    assert any("不是有效的签名内容" in item for item in errors)


def test_signature_url_is_not_accepted_as_signature():
    data = {
        "version": "3.3.2",
        "notes": "x",
        "pub_date": "2026-10-27T00:00:00Z",
        "platforms": {"windows-x86_64": {"signature": "https://example.com/file.sig", "url": "https://github.com/Qiuizi/yijing-workbench-public/releases/download/v3.3.2/a-3.3.2-x64-setup.exe"}},
    }
    errors = manifest.validate_latest_json(data)
    assert any("不能是签名文件链接" in item for item in errors)


@pytest.mark.parametrize("version", ["3.3", "v3.3.2", "3.3.2.1", "3.03.2", ""])
def test_invalid_semver_is_rejected(version):
    with pytest.raises(manifest.UpdaterManifestError):
        manifest.build_latest_json(
            version=version, notes="x", asset_name=f"a-{version}-x64-setup.exe", signature=SIGNATURE,
            repo="Qiuizi/yijing-workbench-public", tag="v3.3.2",
        )


def test_prerelease_version_is_rejected_for_stable_channel():
    data = manifest.build_latest_json(
        version="3.3.2-beta.1", notes="x", asset_name="a-3.3.2-beta.1-x64-setup.exe", signature=SIGNATURE,
        repo="Qiuizi/yijing-workbench-public", tag="v3.3.2-beta.1",
    )
    errors = manifest.validate_latest_json(data, expected_version="3.3.2-beta.1")
    assert any("不允许预发布版本" in item for item in errors)


def test_tag_and_version_mismatch_is_rejected():
    data = manifest.build_latest_json(
        version="3.3.2", notes="x", asset_name="a-3.3.2-x64-setup.exe", signature=SIGNATURE,
        repo="Qiuizi/yijing-workbench-public", tag="v3.3.3",
    )
    errors = manifest.validate_latest_json(data, expected_version="3.3.2", tag="v3.3.2")
    assert any("url 与发布 tag 不一致" in item for item in errors)


def test_release_dir_requires_all_documents(tmp_path):
    from scripts.updater.verify_release import verify

    release = _build_release(tmp_path)
    (release / "PROVENANCE.md").unlink()
    problems = verify(release, tag="v3.3.2", repo="Qiuizi/yijing-workbench-public", production=False, expected_version="3.3.2")
    assert any("PROVENANCE.md" in item for item in problems)


def test_signature_mismatch_between_sig_and_latest_json_is_rejected(tmp_path):
    from scripts.updater.verify_release import verify

    release = _build_release(tmp_path)
    data = json.loads((release / "latest.json").read_text(encoding="utf-8"))
    tampered = _MINISIGN_TEXT.replace("file:test-setup.exe", "file:other-setup.exe")
    data["platforms"]["windows-x86_64"]["signature"] = base64.b64encode(tampered.encode("utf-8")).decode("ascii")
    (release / "latest.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    problems = verify(release, tag="v3.3.2", repo="Qiuizi/yijing-workbench-public", production=False, expected_version="3.3.2")
    assert any("signature 与 .sig 文件内容不一致" in item for item in problems)


def test_production_mode_refuses_qa_public_key(tmp_path):
    """仓库当前内置的是 QA 公钥，正式渠道校验必须拒绝。"""
    from scripts.updater.verify_release import verify

    release = _build_release(tmp_path)
    problems = verify(
        release,
        tag="v3.3.2",
        repo="Qiuizi/yijing-workbench-public",
        production=True,
        expected_version="3.3.2",
        expect_pubkey=FAKE_PUBKEY,
    )
    assert any("QA 测试公钥" in item for item in problems)


def test_production_mode_requires_expect_pubkey(tmp_path):
    from scripts.updater.verify_release import verify

    release = _build_release(tmp_path)
    problems = verify(
        release,
        tag="v3.3.2",
        repo="Qiuizi/yijing-workbench-public",
        production=True,
        expected_version="3.3.2",
    )
    assert any("--expect-pubkey" in item for item in problems)


def test_public_key_mismatch_is_rejected(tmp_path):
    """注入的公钥与 manifest 记录的不一致 → 必须失败。"""
    from scripts.updater.verify_release import verify

    release = _build_release(tmp_path)
    other_key = base64.b64encode(
        ("untrusted comment: minisign public key: OTHER\n"
         + base64.b64encode(b"Ed" + bytes.fromhex("99" * 8) + bytes(32)).decode() + "\n").encode()
    ).decode()
    problems = verify(
        release,
        tag="v3.3.2",
        repo="Qiuizi/yijing-workbench-public",
        production=False,
        expected_version="3.3.2",
        expect_pubkey=other_key,
    )
    assert any("指纹" in item and "不一致" in item for item in problems)


def test_repo_public_key_is_a_valid_minisign_key():
    info = describe_public_key(app_public_key(REPO_ROOT))
    assert info["valid"] is True
    assert info["bytes"] == 42
    assert info["is_qa"] is True, "本轮提交的是 QA 公钥；正式发布前必须替换"


def test_release_gate_refuses_qa_key():
    from scripts.updater.release_gate import check

    ok, message = check("3.3.2")
    assert ok is False
    assert "QA 测试公钥" in message


def test_release_gate_reports_version_mismatch_first():
    from scripts.updater.release_gate import check

    ok, message = check("9.9.9")
    assert ok is False
    assert "不一致" in message


def test_release_gate_refuses_qa_key():
    from scripts.updater.release_gate import check

    ok, message = check("3.3.2")
    assert ok is False
    assert "QA 测试公钥" in message


def test_release_gate_reports_version_mismatch_first():
    from scripts.updater.release_gate import check

    ok, message = check("9.9.9")
    assert ok is False
    assert "不一致" in message


def test_versions_consistent_after_bump():
    assert manifest.assert_versions_consistent(REPO_ROOT) == "3.3.2"


def test_path_helpers_accept_str_root():
    # CLI 里常见 assert_versions_consistent('.')，必须能吃字符串路径
    assert manifest.assert_versions_consistent(str(REPO_ROOT)) == "3.3.2"
    assert app_public_key(str(REPO_ROOT)) == app_public_key(REPO_ROOT)


def test_path_helpers_accept_str_root():
    # CLI 里常见 assert_versions_consistent('.')，必须能吃字符串路径
    assert manifest.assert_versions_consistent(str(REPO_ROOT)) == "3.3.2"
    assert app_public_key(str(REPO_ROOT)) == app_public_key(REPO_ROOT)


def test_site_links_update_is_idempotent():
    source = (REPO_ROOT / "website/src/links.ts").read_text(encoding="utf-8")
    facts = {
        "tag": "v3.3.2",
        "date": "2026-10-27",
        "assetName": "yijing-workbench-3.3.2-x64-setup.exe",
        "bytes": 16111111,
        "sha256": "A" * 64,
        "version": "v3.3.2",
    }
    once = apply_to_source(source, facts)
    twice = apply_to_source(once, facts)
    assert once == twice
    assert "releases/tag/v3.3.2" in once
    assert "yijing-workbench-3.3.2-x64-setup.exe" in once
    assert "export const APP_VERSION = 'v3.3.2'" in once
    assert re.search(r"sha256: 'A{64}'", once)
