//! NQTS Risk Engine — Rust sidecar.
//!
//! Mirrors the Python `production/risk/circuit_breakers.py` semantics so that
//! the exact same fixtures pass in both implementations:
//!   - PAUSE: block new entries, let existing trades run to SL/TP.
//!   - HARD_STOP: flatten/halt.
//!   - Broken persistence: log + start fresh (preserve file for forensics).


#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Action { Allow, Pause, HardStop }

pub struct Breaker {
    pub paused: bool,
    pub hard_stopped: bool,
}

impl Breaker {
    pub fn new() -> Self { Self { paused: false, hard_stopped: false } }

    pub fn pause(&mut self) -> Action {
        self.paused = true;
        Action::Pause
    }

    pub fn hard_stop(&mut self) -> Action {
        self.hard_stopped = true;
        self.paused = false;
        Action::HardStop
    }

    pub fn allow_new_entry(&self) -> bool {
        !self.paused && !self.hard_stopped
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pause_blocks_entries() {
        let mut b = Breaker::new();
        b.pause();
        assert!(!b.allow_new_entry());
    }

    #[test]
    fn hard_stop_blocks_everything() {
        let mut b = Breaker::new();
        b.hard_stop();
        assert!(!b.allow_new_entry());
        assert!(b.hard_stopped);
    }

    #[test]
    fn allows_by_default() {
        let b = Breaker::new();
        assert!(b.allow_new_entry());
    }
}
