//! Atomic JSON persistence for breaker state.
//!
//! Writes go to a temp file in the same directory and are renamed into place so
//! a crash can never leave a half-written state file. A corrupt file is moved
//! aside (kept for forensics) and the caller starts fresh.

use serde::{de::DeserializeOwned, Serialize};
use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};

pub fn save_atomic<T: Serialize>(path: &Path, value: &T) -> std::io::Result<()> {
    let dir = path.parent().unwrap_or_else(|| Path::new("."));
    fs::create_dir_all(dir)?;
    let tmp = dir.join(format!(
        ".{}.tmp",
        path.file_name().and_then(|n| n.to_str()).unwrap_or("state")
    ));
    {
        let mut f = fs::File::create(&tmp)?;
        let bytes = serde_json::to_vec_pretty(value)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;
        f.write_all(&bytes)?;
        f.sync_all()?;
    }
    fs::rename(&tmp, path)
}

pub enum Loaded<T> {
    Value(T),
    Missing,
    /// File was corrupt; it was preserved at the returned path.
    Corrupt(PathBuf),
}

pub fn load<T: DeserializeOwned>(path: &Path) -> std::io::Result<Loaded<T>> {
    if !path.exists() {
        return Ok(Loaded::Missing);
    }
    let bytes = fs::read(path)?;
    match serde_json::from_slice::<T>(&bytes) {
        Ok(v) => Ok(Loaded::Value(v)),
        Err(_) => {
            let preserved = path.with_extension("corrupt");
            fs::rename(path, &preserved)?;
            Ok(Loaded::Corrupt(preserved))
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::WinRateBreaker;

    fn tmpdir(tag: &str) -> PathBuf {
        let p = std::env::temp_dir().join(format!("nqts-risk-{}-{}", tag, std::process::id()));
        let _ = fs::remove_dir_all(&p);
        fs::create_dir_all(&p).unwrap();
        p
    }

    #[test]
    fn roundtrip() {
        let dir = tmpdir("rt");
        let path = dir.join("state.json");
        let mut b = WinRateBreaker::new(0.4, 0.45);
        for _ in 0..25 {
            b.record_trade(-1.0);
        }
        b.check();
        save_atomic(&path, &b).unwrap();
        match load::<WinRateBreaker>(&path).unwrap() {
            Loaded::Value(r) => assert!(r.core.paused),
            _ => panic!("expected value"),
        }
        assert!(!dir.join(".state.json.tmp").exists());
    }

    #[test]
    fn corrupt_file_is_preserved_not_deleted() {
        let dir = tmpdir("corrupt");
        let path = dir.join("state.json");
        fs::write(&path, b"{not json").unwrap();
        match load::<WinRateBreaker>(&path).unwrap() {
            Loaded::Corrupt(p) => {
                assert!(p.exists());
                assert!(!path.exists());
            }
            _ => panic!("expected corrupt"),
        }
    }

    #[test]
    fn missing_is_missing() {
        let dir = tmpdir("missing");
        assert!(matches!(
            load::<WinRateBreaker>(&dir.join("nope.json")).unwrap(),
            Loaded::Missing
        ));
    }
}
