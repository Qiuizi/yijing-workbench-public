/// Isolated verifier compilation sets this to exactly `1`.
/// Any other value, including unset, keeps the normal Tauri build script.
pub fn skip_tauri_build(value: Option<&str>) -> bool {
    value == Some("1")
}

#[cfg(test)]
mod tests {
    use super::skip_tauri_build;

    #[test]
    fn normal_builds_do_not_skip() {
        assert!(!skip_tauri_build(None));
        assert!(!skip_tauri_build(Some("")));
        assert!(!skip_tauri_build(Some("0")));
        assert!(!skip_tauri_build(Some("true")));
        assert!(!skip_tauri_build(Some(" 1")));
        assert!(!skip_tauri_build(Some("1 ")));
    }

    #[test]
    fn isolated_verifier_skips_only_the_exact_switch() {
        assert!(skip_tauri_build(Some("1")));
    }
}
