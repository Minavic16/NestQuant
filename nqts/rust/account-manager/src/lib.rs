//! NQTS Account Registry — multi-account configuration.
//!
//! * Loads `accounts.yaml`, validates it, and exposes per-account risk limits.
//! * Credentials are **never** stored in the file: an account names an
//!   environment variable (`password_env`) that is resolved at runtime.
//! * Canary membership is explicit (`canary: true`) and rollout slices are
//!   deterministic, so the same accounts land in the same stage every time.

use serde::Deserialize;
use std::collections::HashSet;
use std::fmt;

#[derive(Debug, Clone, Deserialize, PartialEq)]
pub struct RiskLimits {
    pub max_dd_pct: f64,
    #[serde(default = "default_open_trades")]
    pub max_open_trades: u32,
}
fn default_open_trades() -> u32 {
    1
}

#[derive(Debug, Clone, Deserialize, PartialEq)]
pub struct Account {
    pub id: String,
    pub broker: String,
    pub server: String,
    pub login: u64,
    pub leverage: u32,
    /// Name of the env var holding the password; never the password itself.
    #[serde(default)]
    pub password_env: Option<String>,
    pub risk: RiskLimits,
    #[serde(default)]
    pub canary: bool,
    #[serde(default = "enabled")]
    pub enabled: bool,
}
fn enabled() -> bool {
    true
}

#[derive(Debug, Deserialize)]
struct File {
    accounts: Vec<Account>,
}

#[derive(Debug, PartialEq)]
pub enum ConfigError {
    Parse(String),
    Empty,
    DuplicateId(String),
    InvalidField { id: String, reason: String },
    InlineSecret(String),
}

impl fmt::Display for ConfigError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ConfigError::Parse(e) => write!(f, "parse error: {e}"),
            ConfigError::Empty => write!(f, "no accounts configured"),
            ConfigError::DuplicateId(i) => write!(f, "duplicate account id: {i}"),
            ConfigError::InvalidField { id, reason } => write!(f, "account {id}: {reason}"),
            ConfigError::InlineSecret(k) => {
                write!(f, "inline secret '{k}' is not allowed; use *_env")
            }
        }
    }
}
impl std::error::Error for ConfigError {}

#[derive(Debug, Clone)]
pub struct Registry {
    accounts: Vec<Account>,
}

/// Keys that must never carry a literal value in the file.
const FORBIDDEN_KEYS: [&str; 4] = ["password:", "token:", "secret:", "api_key:"];

pub fn from_yaml_text(text: &str) -> Result<Registry, ConfigError> {
    for line in text.lines() {
        let t = line.trim_start().trim_start_matches("- ");
        if let Some(k) = FORBIDDEN_KEYS.iter().find(|k| t.starts_with(**k)) {
            return Err(ConfigError::InlineSecret(k.trim_end_matches(':').into()));
        }
    }
    let file: File = serde_yaml::from_str(text).map_err(|e| ConfigError::Parse(e.to_string()))?;
    if file.accounts.is_empty() {
        return Err(ConfigError::Empty);
    }

    let mut seen = HashSet::new();
    for a in &file.accounts {
        if !seen.insert(a.id.clone()) {
            return Err(ConfigError::DuplicateId(a.id.clone()));
        }
        let bad = |reason: &str| ConfigError::InvalidField {
            id: a.id.clone(),
            reason: reason.into(),
        };
        if a.id.trim().is_empty() {
            return Err(bad("empty id"));
        }
        if a.leverage == 0 {
            return Err(bad("leverage must be > 0"));
        }
        if !(a.risk.max_dd_pct > 0.0 && a.risk.max_dd_pct <= 100.0) {
            return Err(bad("max_dd_pct must be in (0,100]"));
        }
        if a.risk.max_open_trades == 0 {
            return Err(bad("max_open_trades must be > 0"));
        }
    }
    Ok(Registry {
        accounts: file.accounts,
    })
}

impl Registry {
    pub fn all(&self) -> &[Account] {
        &self.accounts
    }
    pub fn get(&self, id: &str) -> Option<&Account> {
        self.accounts.iter().find(|a| a.id == id)
    }
    pub fn active(&self) -> impl Iterator<Item = &Account> {
        self.accounts.iter().filter(|a| a.enabled)
    }
    pub fn canaries(&self) -> impl Iterator<Item = &Account> {
        self.active().filter(|a| a.canary)
    }
    pub fn stable(&self) -> impl Iterator<Item = &Account> {
        self.active().filter(|a| !a.canary)
    }

    /// Accounts included at a rollout stage of `pct` percent.
    /// Explicit canaries always go first; remaining slots are filled from the
    /// stable accounts in a deterministic (id-hash) order.
    pub fn rollout_slice(&self, pct: u32) -> Vec<&Account> {
        let pct = pct.min(100) as usize;
        let active: Vec<&Account> = self.active().collect();
        let target = (active.len() * pct).div_ceil(100);
        let mut ordered: Vec<&Account> = self.canaries().collect();
        let mut rest: Vec<&Account> = self.stable().collect();
        rest.sort_by_key(|a| stable_hash(&a.id));
        ordered.extend(rest);
        ordered.truncate(target);
        ordered
    }

    /// Resolve the password for an account from the process environment.
    pub fn resolve_password(
        &self,
        id: &str,
        env: impl Fn(&str) -> Option<String>,
    ) -> Option<String> {
        self.get(id)?.password_env.as_deref().and_then(env)
    }
}

/// FNV-1a: stable across runs and platforms (unlike `DefaultHasher`).
fn stable_hash(s: &str) -> u64 {
    s.bytes().fold(0xcbf29ce484222325, |h, b| {
        (h ^ b as u64).wrapping_mul(0x100000001b3)
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    const OK: &str = r#"
accounts:
  - id: a1
    broker: metatrader5
    server: Demo
    login: 1
    leverage: 100
    password_env: NQTS_A1_PASSWORD
    risk: { max_dd_pct: 5, max_open_trades: 2 }
  - id: c1
    broker: metatrader5
    server: Demo
    login: 2
    leverage: 100
    risk: { max_dd_pct: 2 }
    canary: true
  - id: a2
    broker: metatrader5
    server: Demo
    login: 3
    leverage: 100
    risk: { max_dd_pct: 5 }
  - id: off
    broker: metatrader5
    server: Demo
    login: 4
    leverage: 100
    risk: { max_dd_pct: 5 }
    enabled: false
"#;

    #[test]
    fn loads_and_defaults() {
        let r = from_yaml_text(OK).unwrap();
        assert_eq!(r.all().len(), 4);
        assert_eq!(r.get("c1").unwrap().risk.max_open_trades, 1);
        assert_eq!(r.active().count(), 3);
    }

    #[test]
    fn rejects_inline_secrets() {
        let y = OK.replace("password_env: NQTS_A1_PASSWORD", "password: hunter2");
        assert_eq!(
            from_yaml_text(&y).unwrap_err(),
            ConfigError::InlineSecret("password".into())
        );
    }

    #[test]
    fn rejects_duplicates_and_bad_limits() {
        let dup = OK.replace("id: a2", "id: a1");
        assert_eq!(
            from_yaml_text(&dup).unwrap_err(),
            ConfigError::DuplicateId("a1".into())
        );
        let bad = OK.replace("max_dd_pct: 2 }", "max_dd_pct: 0 }");
        assert!(matches!(
            from_yaml_text(&bad),
            Err(ConfigError::InvalidField { .. })
        ));
        assert_eq!(
            from_yaml_text("accounts: []").unwrap_err(),
            ConfigError::Empty
        );
    }

    #[test]
    fn canary_goes_first_and_slices_are_deterministic() {
        let r = from_yaml_text(OK).unwrap();
        let s10: Vec<_> = r.rollout_slice(10).iter().map(|a| a.id.clone()).collect();
        assert_eq!(s10, vec!["c1"]); // ceil(3*10%) = 1 -> the canary
        let s100: Vec<_> = r.rollout_slice(100).iter().map(|a| a.id.clone()).collect();
        assert_eq!(s100.len(), 3);
        assert_eq!(s100[0], "c1");
        assert!(!s100.contains(&"off".to_string()));
        assert_eq!(
            r.rollout_slice(50)
                .iter()
                .map(|a| a.id.clone())
                .collect::<Vec<_>>(),
            r.rollout_slice(50)
                .iter()
                .map(|a| a.id.clone())
                .collect::<Vec<_>>()
        );
    }

    #[test]
    fn password_is_resolved_from_env_only() {
        let r = from_yaml_text(OK).unwrap();
        let env = |k: &str| (k == "NQTS_A1_PASSWORD").then(|| "s3cret".to_string());
        assert_eq!(r.resolve_password("a1", env).as_deref(), Some("s3cret"));
        assert_eq!(r.resolve_password("c1", env), None);
    }
}
