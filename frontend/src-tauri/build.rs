include!("tauri_build_gate.rs");

fn main() {
    println!("cargo:rerun-if-env-changed=YIJING_SKIP_TAURI_BUILD");
    // Only the Verify Job's isolated `cargo build --bin verify-updater-signature`
    // sets this. Candidate and production desktop builds leave it unset, so
    // tauri_build::build() still packages the sidecar and resources.
    let raw = std::env::var("YIJING_SKIP_TAURI_BUILD").ok();
    if skip_tauri_build(raw.as_deref()) {
        // tauri_build normally declares this cfg. Declaring it here avoids a
        // false warning without packaging the sidecar or frontend.
        println!("cargo:rustc-check-cfg=cfg(mobile)");
        println!("cargo:warning=YIJING_SKIP_TAURI_BUILD=1; skipping tauri_build for the isolated verifier");
        return;
    }
    tauri_build::build();
}
