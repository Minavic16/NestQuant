"""Studio test configuration.

Market-data-dependent tests are gated, not hidden: they skip with an explicit
reason when the pickles are absent and run normally when STUDIO_DATA_DIR (or
NQTS_DATA_DIR, or ./data) holds them. Only the classes listed here are gated;
a FileNotFoundError anywhere else is a real failure.
"""
import pytest

from nestquant_studio.paths import data_dir, has_market_data, output_dir

DATA_DEPENDENT = (
    "tests/legacy/regression/test_phase_s0_breakout.py::TestCausality",
    "tests/legacy/regression/test_phase_s0_breakout.py::TestResultsFile",
    "tests/legacy/regression/test_phase_s0_breakout.py::TestSignalStructure",
    "tests/legacy/regression/test_phase_s0_breakout.py::TestSimulation",
    "tests/legacy/regression/test_signal_discovery.py::TestAdaptiveExtremeness",
    "tests/legacy/regression/test_signal_discovery.py::TestConditionalSurface",
    "tests/legacy/regression/test_signal_discovery.py::TestCostSensitivity",
    "tests/legacy/regression/test_signal_discovery.py::TestEventCount",
    "tests/legacy/regression/test_signal_discovery.py::TestForwardReturn",
    "tests/legacy/regression/test_signal_discovery.py::TestMultipleComparison",
    "tests/legacy/regression/test_signal_discovery.py::TestOutcomeClassification",
    "tests/legacy/regression/test_signal_discovery.py::TestTemporalStability",
    "tests/legacy/regression/test_signal_discovery.py::TestZDynamics",
)


def pytest_configure(config):
    config.addinivalue_line("markers", "requires_data: needs market-data pickles (see tests/conftest.py)")


# Result-validation tests: they assert on JSON produced by running the experiments,
# so they need the experiment outputs, not just the raw data.
RESULTS_DIR = "tests/legacy/experiment_results/"


def pytest_collection_modifyitems(config, items):
    no_data = not has_market_data()
    no_results = not (output_dir().exists() and any(output_dir().rglob("*.json")))
    data_skip = pytest.mark.skip(
        reason=f"market data not found in {data_dir()} (set STUDIO_DATA_DIR / NQTS_DATA_DIR)"
    )
    results_skip = pytest.mark.skip(
        reason=f"experiment outputs not found in {output_dir()} (run the experiments or set STUDIO_OUTPUT_DIR)"
    )
    for item in items:
        nid = item.nodeid
        nid = nid.removeprefix("studio/")
        if no_data and nid.startswith(DATA_DEPENDENT):
            item.add_marker(data_skip)
            item.add_marker(pytest.mark.requires_data)
        elif no_results and nid.startswith(RESULTS_DIR):
            item.add_marker(results_skip)
            item.add_marker(pytest.mark.requires_data)
