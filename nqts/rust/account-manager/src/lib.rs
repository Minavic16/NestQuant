//! NQTS Account Registry — multi-account config loader (TOML-side stub).

#[derive(Debug, Clone)]
pub struct Account {
    pub id: String,
    pub leverage: u32,
    pub canary: bool,
}

pub fn from_yaml_text(_yaml: &str) -> Vec<Account> {
    // Minimal: real parsing uses serde_yaml in Phase 3.
    vec![]
}
