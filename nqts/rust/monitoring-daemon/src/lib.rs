//! NQTS Monitoring — thread-safe metrics registry with Prometheus text output.
//! Metric names follow `contracts/telemetry-contract.md` (`nqts_*`).

use std::collections::BTreeMap;
use std::sync::Mutex;

#[derive(Default)]
struct Inner {
    counters: BTreeMap<String, f64>,
    gauges: BTreeMap<String, f64>,
    /// name -> (bucket upper bounds, bucket counts, sum, count)
    histograms: BTreeMap<String, Hist>,
}

struct Hist {
    bounds: Vec<f64>,
    counts: Vec<u64>,
    sum: f64,
    count: u64,
}

#[derive(Default)]
pub struct Metrics {
    inner: Mutex<Inner>,
}

/// Prometheus metric names: [a-zA-Z_:][a-zA-Z0-9_:]*
fn sanitize(name: &str) -> String {
    let mut s: String = name
        .chars()
        .map(|c| {
            if c.is_ascii_alphanumeric() || c == '_' || c == ':' {
                c
            } else {
                '_'
            }
        })
        .collect();
    if s.chars().next().is_none_or(|c| c.is_ascii_digit()) {
        s.insert(0, '_');
    }
    s
}

impl Metrics {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn inc(&self, name: &str, by: f64) {
        if by < 0.0 {
            return;
        } // counters are monotonic
        *self
            .inner
            .lock()
            .unwrap()
            .counters
            .entry(sanitize(name))
            .or_insert(0.0) += by;
    }

    pub fn set_gauge(&self, name: &str, v: f64) {
        self.inner.lock().unwrap().gauges.insert(sanitize(name), v);
    }

    pub fn observe(&self, name: &str, v: f64, bounds: &[f64]) {
        let mut g = self.inner.lock().unwrap();
        let h = g.histograms.entry(sanitize(name)).or_insert_with(|| Hist {
            bounds: bounds.to_vec(),
            counts: vec![0; bounds.len()],
            sum: 0.0,
            count: 0,
        });
        for (i, b) in h.bounds.iter().enumerate() {
            if v <= *b {
                h.counts[i] += 1;
            }
        }
        h.sum += v;
        h.count += 1;
    }

    pub fn counter(&self, name: &str) -> f64 {
        *self
            .inner
            .lock()
            .unwrap()
            .counters
            .get(&sanitize(name))
            .unwrap_or(&0.0)
    }

    pub fn render(&self) -> String {
        let g = self.inner.lock().unwrap();
        let mut out = String::new();
        for (k, v) in &g.counters {
            out += &format!("# TYPE {k} counter\n{k} {v}\n");
        }
        for (k, v) in &g.gauges {
            out += &format!("# TYPE {k} gauge\n{k} {v}\n");
        }
        for (k, h) in &g.histograms {
            out += &format!("# TYPE {k} histogram\n");
            for (b, c) in h.bounds.iter().zip(&h.counts) {
                out += &format!("{k}_bucket{{le=\"{b}\"}} {c}\n");
            }
            out += &format!(
                "{k}_bucket{{le=\"+Inf\"}} {}\n{k}_sum {}\n{k}_count {}\n",
                h.count, h.sum, h.count
            );
        }
        out
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Arc;

    #[test]
    fn counters_are_monotonic_and_render() {
        let m = Metrics::new();
        m.inc("nqts_signals_total", 1.0);
        m.inc("nqts_signals_total", 2.0);
        m.inc("nqts_signals_total", -5.0); // ignored
        assert_eq!(m.counter("nqts_signals_total"), 3.0);
        assert!(m.render().contains("nqts_signals_total 3"));
    }

    #[test]
    fn names_are_sanitized() {
        let m = Metrics::new();
        m.set_gauge("1bad name-x", 1.5);
        assert!(m.render().contains("_1bad_name_x 1.5"));
    }

    #[test]
    fn histogram_buckets_are_cumulative() {
        let m = Metrics::new();
        for v in [5.0, 50.0, 500.0] {
            m.observe("nqts_fill_latency_ms", v, &[10.0, 100.0]);
        }
        let r = m.render();
        assert!(r.contains("nqts_fill_latency_ms_bucket{le=\"10\"} 1"));
        assert!(r.contains("nqts_fill_latency_ms_bucket{le=\"100\"} 2"));
        assert!(r.contains("nqts_fill_latency_ms_bucket{le=\"+Inf\"} 3"));
        assert!(r.contains("nqts_fill_latency_ms_count 3"));
    }

    #[test]
    fn safe_across_threads() {
        let m = Arc::new(Metrics::new());
        let hs: Vec<_> = (0..8)
            .map(|_| {
                let m = m.clone();
                std::thread::spawn(move || {
                    for _ in 0..1000 {
                        m.inc("n", 1.0)
                    }
                })
            })
            .collect();
        hs.into_iter().for_each(|h| h.join().unwrap());
        assert_eq!(m.counter("n"), 8000.0);
    }
}
