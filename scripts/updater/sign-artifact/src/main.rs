//! Sign an installer with the same minisign shape Tauri CLI 2.11.5 writes.
//!
//! The private key is read from a file. The password comes from
//! `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` and is never printed. This program
//! does not rebuild an installer and refuses to follow a symlink.

use std::env;
use std::fs;
use std::io::Cursor;
use std::path::Path;
use std::process::ExitCode;
use std::time::{SystemTime, UNIX_EPOCH};

use base64::Engine;
use minisign::{sign, SecretKey, SecretKeyBox};
use sha2::{Digest, Sha256};

fn fail(message: &str) -> ExitCode {
    eprintln!("FAIL  {message}");
    ExitCode::from(1)
}

fn arg_value(name: &str) -> Option<String> {
    let args: Vec<String> = env::args().collect();
    let mut index = 1;
    while index + 1 < args.len() {
        if args[index] == name {
            return Some(args[index + 1].clone());
        }
        index += 1;
    }
    None
}

fn sha256_file(path: &Path) -> Result<String, String> {
    let bytes = fs::read(path).map_err(|error| format!("cannot read {}: {error}", path.display()))?;
    Ok(format!("{:x}", Sha256::digest(bytes)))
}

fn key_material(raw: &str) -> Result<String, String> {
    let text = raw.trim().trim_start_matches('\u{feff}');
    if text.contains("untrusted comment:") {
        return Ok(text.to_string());
    }
    let decoded = base64::engine::general_purpose::STANDARD
        .decode(text)
        .map_err(|_| "signing key is neither a minisign key nor base64".to_string())?;
    let text = String::from_utf8(decoded).map_err(|_| "signing key is not utf-8".to_string())?;
    if !text.contains("untrusted comment:") {
        return Err("decoded signing key is not a minisign secret key".to_string());
    }
    Ok(text)
}

fn load_secret(raw: &str, password: &str) -> Result<SecretKey, String> {
    let text = key_material(raw)?;
    let boxed = SecretKeyBox::from_string(&text).map_err(|_| "cannot parse signing key".to_string())?;
    boxed
        .into_secret_key(Some(password.to_string()))
        .map_err(|_| "incorrect updater private key password".to_string())
}

fn key_id_from_signature(signature_text: &str) -> Result<String, String> {
    let line = signature_text
        .lines()
        .nth(1)
        .ok_or_else(|| "signature is missing its key id line".to_string())?;
    let raw = base64::engine::general_purpose::STANDARD
        .decode(line.trim())
        .map_err(|_| "signature key id line is not base64".to_string())?;
    if raw.len() < 10 {
        return Err("signature key id is truncated".to_string());
    }
    Ok(raw[2..10].iter().map(|byte| format!("{byte:02X}")).collect())
}

fn sign_installer(secret: &SecretKey, installer: &Path, signature_out: &Path, version: &str) -> Result<(), String> {
    if version.contains(['\t', '\r', '\n']) {
        return Err("version cannot contain a tab or newline".to_string());
    }
    let metadata = fs::symlink_metadata(installer).map_err(|error| error.to_string())?;
    if metadata.file_type().is_symlink() || !metadata.is_file() {
        return Err("refusing to sign a symlink or non-regular file".to_string());
    }
    let before = sha256_file(installer)?;
    let payload = fs::read(installer).map_err(|error| error.to_string())?;
    let filename = installer
        .file_name()
        .and_then(|name| name.to_str())
        .ok_or_else(|| "installer name is not utf-8".to_string())?;
    let timestamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|error| error.to_string())?
        .as_secs();
    let trusted = format!("timestamp:{timestamp}\tfile:{filename}\tversion:{version}");
    let signature = sign(
        None,
        secret,
        Cursor::new(payload),
        Some(trusted.as_str()),
        Some("signature from tauri secret key"),
    )
    .map_err(|_| "failed to sign installer".to_string())?;
    let signature_text = signature.into_string();
    let _key_id = key_id_from_signature(&signature_text)?;
    let encoded = base64::engine::general_purpose::STANDARD.encode(signature_text);
    if let Some(parent) = signature_out.parent() {
        fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    }
    fs::write(signature_out, encoded.as_bytes()).map_err(|error| error.to_string())?;
    let after = sha256_file(installer)?;
    if before != after {
        return Err("installer bytes changed while signing".to_string());
    }
    Ok(())
}

fn main() -> ExitCode {
    let (Some(file), Some(key_file), Some(signature_out), Some(version)) = (
        arg_value("--file"),
        arg_value("--key-file"),
        arg_value("--signature-out"),
        arg_value("--version"),
    ) else {
        eprintln!("usage: sign-artifact --file <installer> --key-file <secret> --signature-out <sig> --version <version>");
        return ExitCode::from(2);
    };
    let password = match env::var("TAURI_SIGNING_PRIVATE_KEY_PASSWORD") {
        Ok(value) => value,
        Err(_) => return fail("TAURI_SIGNING_PRIVATE_KEY_PASSWORD is not set"),
    };
    let raw = match fs::read_to_string(&key_file) {
        Ok(value) => value,
        Err(_) => return fail("cannot read signing key file"),
    };
    let secret = match load_secret(&raw, &password) {
        Ok(value) => value,
        Err(error) => return fail(&error),
    };
    if let Err(error) = sign_installer(&secret, Path::new(&file), Path::new(&signature_out), &version) {
        return fail(&error);
    }
    println!("OK  signed");
    ExitCode::SUCCESS
}

#[cfg(test)]
mod tests {
    use super::{key_id_from_signature, load_secret, sign_installer};
    use minisign::KeyPair;
    use minisign_verify::{PublicKey, Signature};
    use std::fs;

    #[test]
    fn signature_matches_minisign_verify_and_does_not_change_bytes() {
        let dir = std::env::temp_dir().join(format!("sign-artifact-{}", std::process::id()));
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        let KeyPair { pk, sk } = KeyPair::generate_encrypted_keypair(Some("pw".into())).unwrap();
        let raw = sk.to_box(None).unwrap().to_string();
        let secret = load_secret(&raw, "pw").unwrap();
        assert!(load_secret(&raw, "nope").is_err());
        let installer = dir.join("yijing-workbench-3.3.2-x64-setup.exe");
        fs::write(&installer, b"installer-bytes").unwrap();
        let signature_out = dir.join("installer.sig");
        sign_installer(&secret, &installer, &signature_out, "3.3.2").unwrap();
        assert_eq!(fs::read(&installer).unwrap(), b"installer-bytes");
        let encoded = fs::read_to_string(&signature_out).unwrap();
        let text = String::from_utf8(base64::Engine::decode(&base64::engine::general_purpose::STANDARD, encoded).unwrap()).unwrap();
        assert!(text.contains("\tversion:3.3.2"));
        assert!(text.contains("signature from tauri secret key"));
        let public_key = PublicKey::decode(&pk.to_box().unwrap().to_string()).unwrap();
        let signature = Signature::decode(&text).unwrap();
        public_key.verify(b"installer-bytes", &signature, true).unwrap();
        assert_eq!(key_id_from_signature(&text).unwrap().len(), 16);
        let _ = fs::remove_dir_all(&dir);
    }
}
