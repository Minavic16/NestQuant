//! Parity test: replay the shared fixtures (generated from the Python reference
//! implementation) through the Rust breakers and require identical outcomes.

use nqts_risk_engine::*;
use serde::Deserialize;
use std::path::PathBuf;

#[derive(Deserialize)]
struct Expect {
    name: String,
    triggered: bool,
    paused: bool,
    hard_stopped: bool,
    events: usize,
}

#[derive(Deserialize)]
struct WinRateCase {
    #[serde(flatten)]
    e: Expect,
    pnls: Vec<f64>,
}
#[derive(Deserialize)]
struct SlipCase {
    #[serde(flatten)]
    e: Expect,
    slippages: Vec<f64>,
}
#[derive(Deserialize)]
struct DdCase {
    #[serde(flatten)]
    e: Expect,
    steps: Vec<[f64; 2]>,
}
#[derive(Deserialize)]
struct Fixtures {
    winrate: Vec<WinRateCase>,
    slippage: Vec<SlipCase>,
    drawdown_pace: Vec<DdCase>,
    profit_factor: Vec<WinRateCase>,
}

fn load() -> Fixtures {
    let p =
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../../contracts/fixtures/breakers.json");
    serde_json::from_slice(&std::fs::read(&p).unwrap_or_else(|e| panic!("{}: {e}", p.display())))
        .unwrap()
}

fn assert_matches(e: &Expect, triggered: bool, core: &Core) {
    assert_eq!(triggered, e.triggered, "{}: triggered", e.name);
    assert_eq!(core.paused, e.paused, "{}: paused", e.name);
    assert_eq!(
        core.hard_stopped, e.hard_stopped,
        "{}: hard_stopped",
        e.name
    );
    assert_eq!(core.events.len(), e.events, "{}: events", e.name);
}

#[test]
fn winrate_parity() {
    for c in load().winrate {
        let mut b = WinRateBreaker::new(0.40, 0.45);
        c.pnls.iter().for_each(|p| b.record_trade(*p));
        let t = b.check();
        assert_matches(&c.e, t, &b.core);
    }
}

#[test]
fn slippage_parity() {
    for c in load().slippage {
        let mut b = SlippageBreaker::new(4.8, 3, 6.0);
        c.slippages.iter().for_each(|s| b.record_slippage(*s));
        let t = b.check();
        assert_matches(&c.e, t, &b.core);
    }
}

#[test]
fn drawdown_pace_parity() {
    for c in load().drawdown_pace {
        let mut b = DrawdownPaceBreaker::new(6.0, 15, 9.0, 25);
        c.steps.iter().for_each(|[eq, pk]| b.record_trade(*eq, *pk));
        let t = b.check();
        assert_matches(&c.e, t, &b.core);
    }
}

#[test]
fn profit_factor_parity() {
    for c in load().profit_factor {
        let mut b = ProfitFactorBreaker::new(1.0, 20);
        c.pnls.iter().for_each(|p| b.record_trade(*p));
        let t = b.check();
        assert_matches(&c.e, t, &b.core);
    }
}
