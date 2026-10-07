//! NQTS Risk Engine — Rust implementation of the circuit-breaker suite.
//!
//! Semantics mirror `nestquant/production/risk/circuit_breakers.py` exactly.
//! Both implementations are validated against the shared fixtures in
//! `contracts/fixtures/breakers.json`.
//!
//! * `pause`      — block new entries, existing trades run to SL/TP.
//! * `hard_stop`  — flatten + halt. As in Python, a hard stop also sets `paused`.

use serde::{Deserialize, Serialize};
use std::collections::VecDeque;

pub mod persistence;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Action {
    Allow,
    Pause,
    HardStop,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Event {
    pub breaker: String,
    #[serde(rename = "type")]
    pub kind: String,
    pub message: String,
    pub value: f64,
}

/// State shared by every breaker.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct Core {
    pub name: String,
    pub paused: bool,
    pub hard_stopped: bool,
    pub events: Vec<Event>,
}

impl Core {
    fn new(name: &str) -> Self {
        Self {
            name: name.into(),
            ..Default::default()
        }
    }
    pub fn triggered(&self) -> bool {
        self.paused || self.hard_stopped
    }
    fn trigger(&mut self, kind: &str, message: String, value: f64) {
        self.events.push(Event {
            breaker: self.name.clone(),
            kind: kind.into(),
            message,
            value,
        });
    }
    pub fn pause(&mut self) {
        self.paused = true;
    }
    pub fn unpause(&mut self) {
        self.paused = false;
    }
    pub fn hard_stop(&mut self) {
        self.hard_stopped = true;
        self.paused = true;
    }
    pub fn reset(&mut self) {
        self.paused = false;
        self.hard_stopped = false;
        self.events.clear();
    }
    pub fn action(&self) -> Action {
        if self.hard_stopped {
            Action::HardStop
        } else if self.paused {
            Action::Pause
        } else {
            Action::Allow
        }
    }
}

fn mean<'a, I: IntoIterator<Item = &'a f64>>(it: I) -> f64 {
    let (s, n) = it
        .into_iter()
        .fold((0.0, 0usize), |(s, n), v| (s + v, n + 1));
    if n == 0 {
        0.0
    } else {
        s / n as f64
    }
}

fn push_bounded<T>(q: &mut VecDeque<T>, v: T, cap: usize) {
    if q.len() == cap {
        q.pop_front();
    }
    q.push_back(v);
}

// ---------------------------------------------------------------- WinRate

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WinRateBreaker {
    pub core: Core,
    pub window_20: f64,
    pub window_30: f64,
    results: VecDeque<f64>,
}

impl WinRateBreaker {
    pub fn new(window_20: f64, window_30: f64) -> Self {
        Self {
            core: Core::new("winrate"),
            window_20,
            window_30,
            results: VecDeque::new(),
        }
    }
    pub fn record_trade(&mut self, pnl: f64) {
        push_bounded(&mut self.results, if pnl > 0.0 { 1.0 } else { 0.0 }, 30);
    }
    pub fn check(&mut self) -> bool {
        let mut triggered = false;
        if self.results.len() >= 20 {
            let last20: Vec<f64> = self
                .results
                .iter()
                .skip(self.results.len() - 20)
                .cloned()
                .collect();
            let wr = mean(&last20);
            if wr < self.window_20 {
                self.core.trigger(
                    "pause",
                    format!(
                        "WR over 20t={:.1}% < {:.0}%",
                        wr * 100.0,
                        self.window_20 * 100.0
                    ),
                    wr,
                );
                self.core.pause();
                triggered = true;
            }
        }
        if self.results.len() >= 30 {
            let wr = mean(&self.results);
            if wr < self.window_30 {
                self.core.trigger(
                    "pause",
                    format!(
                        "WR over 30t={:.1}% < {:.0}%",
                        wr * 100.0,
                        self.window_30 * 100.0
                    ),
                    wr,
                );
                self.core.pause();
                triggered = true;
            }
        }
        triggered
    }
}

// --------------------------------------------------------------- Slippage

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SlippageBreaker {
    pub core: Core,
    pub consecutive_threshold: f64,
    pub consecutive_count: u32,
    pub avg_10_threshold: f64,
    slippages: VecDeque<f64>,
    streak: u32,
}

impl SlippageBreaker {
    pub fn new(consecutive_threshold: f64, consecutive_count: u32, avg_10_threshold: f64) -> Self {
        Self {
            core: Core::new("slippage"),
            consecutive_threshold,
            consecutive_count,
            avg_10_threshold,
            slippages: VecDeque::new(),
            streak: 0,
        }
    }
    pub fn record_slippage(&mut self, pips: f64) {
        push_bounded(&mut self.slippages, pips, 10);
        if pips > self.consecutive_threshold {
            self.streak += 1;
        } else {
            self.streak = 0;
        }
    }
    pub fn check(&mut self) -> bool {
        let mut triggered = false;
        if self.streak >= self.consecutive_count {
            self.core.trigger(
                "pause",
                format!(
                    "{} consecutive trades >{}pips",
                    self.streak, self.consecutive_threshold
                ),
                self.streak as f64,
            );
            self.core.pause();
            triggered = true;
        }
        if self.slippages.len() >= 10 {
            let avg = mean(&self.slippages);
            if avg > self.avg_10_threshold {
                self.core.trigger(
                    "pause",
                    format!(
                        "10-trade avg slippage={:.1}pips > {}pips",
                        avg, self.avg_10_threshold
                    ),
                    avg,
                );
                self.core.pause();
                triggered = true;
            }
        }
        triggered
    }
}

// ----------------------------------------------------------- DrawdownPace

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DrawdownPaceBreaker {
    pub core: Core,
    pub soft_dd: f64,
    pub soft_trades: u32,
    pub hard_dd: f64,
    pub hard_trades: u32,
    trade_count: u32,
    current_dd: f64,
}

impl DrawdownPaceBreaker {
    pub fn new(soft_dd: f64, soft_trades: u32, hard_dd: f64, hard_trades: u32) -> Self {
        Self {
            core: Core::new("drawdown_pace"),
            soft_dd,
            soft_trades,
            hard_dd,
            hard_trades,
            trade_count: 0,
            current_dd: 0.0,
        }
    }
    pub fn record_trade(&mut self, equity: f64, peak: f64) {
        self.trade_count += 1;
        self.current_dd = if peak > 0.0 {
            (peak - equity) / peak * 100.0
        } else {
            0.0
        };
    }
    pub fn check(&mut self) -> bool {
        if self.trade_count <= self.hard_trades && self.current_dd >= self.hard_dd {
            self.core.trigger(
                "hard_stop",
                format!(
                    "DD={:.1}% >= {:.0}% at trade {} (limit={})",
                    self.current_dd, self.hard_dd, self.trade_count, self.hard_trades
                ),
                self.current_dd,
            );
            self.core.hard_stop();
            true
        } else if self.trade_count <= self.soft_trades && self.current_dd >= self.soft_dd {
            self.core.trigger(
                "pause",
                format!(
                    "DD={:.1}% >= {:.0}% at trade {}",
                    self.current_dd, self.soft_dd, self.trade_count
                ),
                self.current_dd,
            );
            self.core.pause();
            true
        } else {
            false
        }
    }
}

// ----------------------------------------------------------- ProfitFactor

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProfitFactorBreaker {
    pub core: Core,
    pub threshold: f64,
    pub window: usize,
    pnls: VecDeque<f64>,
}

impl ProfitFactorBreaker {
    pub fn new(threshold: f64, window: usize) -> Self {
        Self {
            core: Core::new("profit_factor"),
            threshold,
            window,
            pnls: VecDeque::new(),
        }
    }
    pub fn record_trade(&mut self, pnl: f64) {
        push_bounded(&mut self.pnls, pnl, self.window);
    }
    pub fn profit_factor(&self) -> Option<f64> {
        let wins: f64 = self.pnls.iter().filter(|p| **p > 0.0).sum();
        let losses: f64 = self.pnls.iter().filter(|p| **p < 0.0).sum();
        if losses == 0.0 {
            None
        } else {
            Some(wins / losses.abs())
        }
    }
    pub fn check(&mut self) -> bool {
        if self.pnls.len() < self.window {
            return false;
        }
        match self.profit_factor() {
            Some(pf) if pf < self.threshold => {
                self.core.trigger(
                    "pause",
                    format!("PF over {}t={:.3} < {:.0}", self.window, pf, self.threshold),
                    pf,
                );
                self.core.pause();
                true
            }
            _ => false,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn hard_stop_also_pauses_like_python() {
        let mut c = Core::new("x");
        c.hard_stop();
        assert!(c.paused && c.hard_stopped);
        assert_eq!(c.action(), Action::HardStop);
    }

    #[test]
    fn pause_then_unpause() {
        let mut c = Core::new("x");
        c.pause();
        assert_eq!(c.action(), Action::Pause);
        c.unpause();
        assert_eq!(c.action(), Action::Allow);
    }

    #[test]
    fn reset_clears_everything() {
        let mut c = Core::new("x");
        c.hard_stop();
        c.trigger("hard_stop", "m".into(), 1.0);
        c.reset();
        assert_eq!(c.action(), Action::Allow);
        assert!(c.events.is_empty());
    }
}
