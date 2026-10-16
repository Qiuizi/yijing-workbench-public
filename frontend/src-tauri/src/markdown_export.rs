use std::{
    fs::File,
    io::{self, Write},
    path::Path,
};
use tempfile::NamedTempFile;

pub(crate) fn save(path: &Path, bytes: &[u8]) -> io::Result<()> {
    save_with(path, |file| file.write_all(bytes))
}

// Stage in the destination directory so persist never needs a cross-volume copy.
// On Windows tempfile uses MoveFileExW(MOVEFILE_REPLACE_EXISTING), without
// deleting/truncating the destination first. This is not a power-loss guarantee.
fn save_with(path: &Path, write: impl FnOnce(&mut File) -> io::Result<()>) -> io::Result<()> {
    let parent = path.parent()
        .filter(|p| !p.as_os_str().is_empty())
        .unwrap_or(Path::new("."));
    let mut staged = NamedTempFile::new_in(parent)?;
    if let Err(error) = write(staged.as_file_mut()).and_then(|_| staged.as_file().sync_all()) {
        return Err(discard(staged, error));
    }
    match staged.persist(path) {
        Ok(_) => Ok(()),
        Err(error) => Err(discard(error.file, error.error)),
    }
}

fn discard(staged: NamedTempFile, error: io::Error) -> io::Error {
    let temporary_path = staged.path().to_owned();
    match staged.close() {
        Ok(()) => error,
        Err(cleanup) => io::Error::new(
            error.kind(),
            format!("{error}；临时文件清理失败（{}）：{cleanup}", temporary_path.display()),
        ),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    fn entries(path: &Path) -> usize {
        fs::read_dir(path).unwrap().count()
    }

    #[test]
    fn chinese_path_utf8_and_existing_destination() {
        let root = tempfile::tempdir().unwrap();
        let directory = root.path().join("中文目录");
        fs::create_dir(&directory).unwrap();
        let path = directory.join("合成起卦.md");
        save(&path, "# 卦象 ☰\n\n中文传统取辞".as_bytes()).unwrap();
        assert_eq!(fs::read(&path).unwrap(), "# 卦象 ☰\n\n中文传统取辞".as_bytes());
        save(&path, "# 确认覆盖".as_bytes()).unwrap();
        assert_eq!(fs::read_to_string(&path).unwrap(), "# 确认覆盖");
        assert_eq!(entries(&directory), 1);
    }

    #[test]
    fn partial_staged_write_failure_preserves_original_and_cleans_temporary_file() {
        let directory = tempfile::tempdir().unwrap();
        let path = directory.path().join("原记录.md");
        fs::write(&path, b"ORIGINAL_SYNTHETIC").unwrap();
        let error = save_with(&path, |file| {
            file.write_all(b"PARTIAL_REPLACEMENT")?;
            Err(io::Error::new(io::ErrorKind::WriteZero, "injected write failure"))
        }).unwrap_err();
        assert_eq!(error.kind(), io::ErrorKind::WriteZero);
        assert_eq!(fs::read(&path).unwrap(), b"ORIGINAL_SYNTHETIC");
        assert_eq!(entries(directory.path()), 1);
    }

    #[test]
    fn failed_new_export_does_not_leave_destination_or_temporary_file() {
        let directory = tempfile::tempdir().unwrap();
        let path = directory.path().join("新记录.md");
        assert!(save_with(&path, |file| {
            file.write_all(b"PARTIAL")?;
            Err(io::Error::new(io::ErrorKind::WriteZero, "injected write failure"))
        }).is_err());
        assert!(!path.exists());
        assert_eq!(entries(directory.path()), 0);
    }

    #[test]
    fn replacement_failure_preserves_destination_and_cleans_temporary_file() {
        let directory = tempfile::tempdir().unwrap();
        let path = directory.path().join("同名目录.md");
        fs::create_dir(&path).unwrap();
        fs::write(path.join("保留.txt"), b"ORIGINAL_SYNTHETIC").unwrap();
        assert!(save(&path, b"REPLACEMENT").is_err());
        assert_eq!(fs::read(path.join("保留.txt")).unwrap(), b"ORIGINAL_SYNTHETIC");
        assert_eq!(entries(directory.path()), 1);
    }

    #[cfg(windows)]
    #[test]
    fn windows_locked_destination_is_preserved_and_temporary_file_is_cleaned() {
        use std::os::windows::fs::OpenOptionsExt;
        let directory = tempfile::tempdir().unwrap();
        let path = directory.path().join("占用的原记录.md");
        fs::write(&path, b"ORIGINAL_SYNTHETIC").unwrap();
        let locked = fs::OpenOptions::new().read(true).share_mode(0).open(&path).unwrap();
        assert!(save(&path, b"REPLACEMENT").is_err());
        assert_eq!(entries(directory.path()), 1);
        drop(locked);
        assert_eq!(fs::read(&path).unwrap(), b"ORIGINAL_SYNTHETIC");
    }

    #[cfg(windows)]
    #[test]
    fn windows_readonly_destination_is_preserved_and_temporary_file_is_cleaned() {
        let directory = tempfile::tempdir().unwrap();
        let path = directory.path().join("只读原记录.md");
        fs::write(&path, b"ORIGINAL_SYNTHETIC").unwrap();
        let mut permissions = fs::metadata(&path).unwrap().permissions();
        permissions.set_readonly(true);
        fs::set_permissions(&path, permissions).unwrap();
        let result = save(&path, b"REPLACEMENT");
        let original = fs::read(&path).unwrap();
        let count = entries(directory.path());
        let mut permissions = fs::metadata(&path).unwrap().permissions();
        permissions.set_readonly(false);
        fs::set_permissions(&path, permissions).unwrap();
        assert!(result.is_err());
        assert_eq!(original, b"ORIGINAL_SYNTHETIC");
        assert_eq!(count, 1);
    }
}
