//! 独立校验 Tauri updater 的 `.sig` 与安装包是否匹配。
//!
//! 目的：把「签名能不能被这把公钥验过」从人工检查变成可执行门禁。
//! 用法（由 scripts/updater/verify_release.py --signature-verifier 调用）：
//!
//!   verify-updater-signature \
//!     --file      yijing-workbench-3.3.2-x64-setup.exe \
//!     --signature signature.minisign.txt   # base64 解码后的 4 行 minisign 文本 \
//!     --pubkey    pubkey.minisign.txt      # base64 解码后的 2 行 minisign 公钥
//!
//! 退出码：0 通过；1 验证失败；2 参数/IO 错误。
//!
//! 用的是 Tauri updater 内部同一套算法（minisign-verify），
//! 因此这里通过 == 安装时能验过；这里失败 == 用户装不上。

use std::fs;
use std::process::ExitCode;

use minisign_verify::{Error, PublicKey, Signature};

fn arg_value(name: &str) -> Option<String> {
    let args: Vec<String> = std::env::args().collect();
    let mut index = 1;
    while index + 1 < args.len() {
        if args[index] == name {
            return Some(args[index + 1].clone());
        }
        index += 1;
    }
    None
}

fn fail(message: &str) -> ExitCode {
    eprintln!("FAIL  {message}");
    ExitCode::from(1)
}

fn main() -> ExitCode {
    let (Some(file), Some(signature_path), Some(pubkey_path)) = (
        arg_value("--file"),
        arg_value("--signature"),
        arg_value("--pubkey"),
    ) else {
        eprintln!("usage: verify-updater-signature --file <artifact> --signature <text> --pubkey <text>");
        return ExitCode::from(2);
    };

    let Ok(payload) = fs::read(&file) else {
        eprintln!("cannot read artifact: {file}");
        return ExitCode::from(2);
    };
    let Ok(signature_text) = fs::read_to_string(&signature_path) else {
        eprintln!("cannot read signature text: {signature_path}");
        return ExitCode::from(2);
    };
    let Ok(pubkey_text) = fs::read_to_string(&pubkey_path) else {
        eprintln!("cannot read public key text: {pubkey_path}");
        return ExitCode::from(2);
    };

    let public_key = match PublicKey::decode(&pubkey_text) {
        Ok(key) => key,
        Err(error) => return fail(&format!("public key decode failed: {error}")),
    };
    let signature = match Signature::decode(&signature_text) {
        Ok(signature) => signature,
        Err(error) => return fail(&format!("signature decode failed: {error}")),
    };

    // allow_legacy=true：Tauri 的签名是预哈希（prehashed）格式
    match public_key.verify(&payload, &signature, true) {
        Ok(()) => {
            println!("OK    signature verified for {}", file);
            ExitCode::SUCCESS
        }
        Err(Error::UnexpectedKeyId) => {
            fail("key id mismatch: 公钥与签名不是同一把钥匙（正式构建注入的公钥与私钥不匹配）")
        }
        Err(Error::InvalidSignature) => fail("signature is invalid: 安装包被改动，或签名不是针对这个文件生成的"),
        Err(Error::UnexpectedAlgorithm) => fail("unexpected algorithm: 签名格式不是 Tauri updater 使用的 minisign 预哈希"),
        Err(error) => fail(&format!("signature verification failed: {error}")),
    }
}
