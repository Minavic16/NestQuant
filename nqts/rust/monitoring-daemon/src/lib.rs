//! NQTS Monitoring Daemon — metrics surface (Prometheus-compatible later).

pub struct Metrics {
    pub signals: u64,
    pub orders: u64,
    pub errors: u64,
}

impl Metrics {
    pub fn new() -> Self { Self { signals: 0, orders: 0, errors: 0 } }
    pub fn snapshot(&self) -> (u64, u64, u64) { (self.signals, self.orders, self.errors) }
}
