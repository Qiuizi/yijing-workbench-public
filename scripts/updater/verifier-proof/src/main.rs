//! Generate a password-protected minisign signature and check the real verifier.
//!
//! This is a test program, not a release tool. It refuses to continue unless
//! VERIFIER_EXE points at the independently compiled verify-updater-signature binary.

use std::env;
use std::fs;
use std::io::Cursor;
use std::path::PathBuf;
use std::process::Command;

use minisign::{KeyPair, SecretKeyBox};

const PASSWORD: &str = "candidate-ephemeral";
const PAYLOAD: &[u8] = b"candidate-bytes";

fn verifier() -> PathBuf {
    PathBuf::from(env::var("VERIFIER_EXE").expect("VERIFIER_EXE is required"))
}

fn run_verifier(file: &std::path::Path, signature: &str, pubkey: &str) -> std::process::ExitStatus {
    let dir = file.parent().expect("file directory");
    let signature_path = dir.join("signature.minisign.txt");
    let pubkey_path = dir.join("pubkey.minisign.txt");
    fs::write(&signature_path, signature).expect("write signature");
    fs::write(&pubkey_path, pubkey).expect("write pubkey");
    Command::new(verifier())
        .arg("--file")
        .arg(file)
        .arg("--signature")
        .arg(&signature_path)
        .arg("--pubkey")
        .arg(&pubkey_path)
        .status()
        .expect("run verifier")
}

fn expect_success(status: std::process::ExitStatus, label: &str) {
    assert!(status.success(), "{label} should pass, exit {status}");
}

fn expect_failure(status: std::process::ExitStatus, label: &str) {
    assert!(!status.success(), "{label} should fail, exit {status}");
}

fn main() {
    let root = PathBuf::from(env::var("PROOF_DIR").expect("PROOF_DIR is required"));
    fs::create_dir_all(&root).expect("proof dir");
    let KeyPair { pk, sk } = KeyPair::generate_encrypted_keypair(Some(PASSWORD.to_string()))
        .expect("generate encrypted keypair");
    let secret_box = sk.to_box(None).expect("secret box").to_string();
    let secret_path = root.join("secret.key");
    fs::write(&secret_path, &secret_box).expect("write secret");
    assert!(
        SecretKeyBox::from_string(&secret_box)
            .expect("parse box")
            .into_secret_key(Some("wrong-password".to_string()))
            .is_err(),
        "wrong password must not unlock the signing key"
    );
    let unlocked = SecretKeyBox::from_string(&secret_box)
        .expect("parse box")
        .into_secret_key(Some(PASSWORD.to_string()))
        .expect("correct password unlocks the signing key");

    let signature = minisign::sign(Some(&pk), &unlocked, Cursor::new(PAYLOAD), None, None)
        .expect("sign with the correct password")
        .into_string();
    let pubkey = pk.to_box().expect("public box").to_string();
    let file = root.join("payload.bin");
    fs::write(&file, PAYLOAD).expect("write payload");
    expect_success(run_verifier(&file, &signature, &pubkey), "valid signature");

    let tampered = root.join("tampered.bin");
    fs::write(&tampered, b"candidate-bytes!").expect("write tampered");
    expect_failure(run_verifier(&tampered, &signature, &pubkey), "modified installer bytes");

    let mut lines: Vec<String> = signature.lines().map(str::to_string).collect();
    let mut chars: Vec<char> = lines[1].chars().collect();
    // Past the 10-byte algorithm+key-id prefix, so the key id stays and only
    // the signature bytes change. The replacement stays inside the base64 alphabet.
    let index = 24;
    chars[index] = if chars[index] == 'A' { 'B' } else { 'A' };
    lines[1] = chars.into_iter().collect();
    expect_failure(
        run_verifier(&file, &lines.join("\n"), &pubkey),
        "modified signature bytes with the original key id",
    );

    let other = KeyPair::generate_encrypted_keypair(Some(PASSWORD.to_string())).expect("other key");
    let other_pub = other.pk.to_box().expect("other public box").to_string();
    expect_failure(run_verifier(&file, &signature, &other_pub), "wrong public key");
    expect_failure(run_verifier(&file, "not-a-signature\n", &pubkey), "invalid encoding");

    // The published minisign-verify prehashed vector must pass our Tauri-compatible verifier.
    let vector_file = root.join("vector.bin");
    fs::write(&vector_file, b"test").expect("vector");
    let vector_signature = "untrusted comment: signature from minisign secret key\n\
RUQf6LRCGA9i559r3g7V1qNyJDApGip8MfqcadIgT9CuhV3EMhHoN1mGTkUidF/z7SrlQgXdy8ofjb7bNJJylDOocrCo8KLzZwo=\n\
trusted comment: timestamp:1556193335\tfile:test\n\
y/rUw2y8/hOUYjZU71eHp/Wo1KZ40fGy2VJEDl34XMJM+TX48Ss/17u3IvIfbVR1FkZZSNCisQbuQY+bHwhEBg==\n";
    let vector_pubkey = "\
untrusted comment: minisign public key: E7620F1842B4E81F
RWQf6LRCGA9i53mlYecO4IzT51TGPpvWucNSCh1CBM0QTaLn73Y7GFO3
";
    expect_success(
        run_verifier(&vector_file, vector_signature, vector_pubkey),
        "Tauri-compatible prehashed vector",
    );
    println!("OK  independent verifier rejected invalid signatures");
}
