"""Research-analysis tests (moved from NQTS test_monitoring.py).

ResearchAnalyzer is research code; it lives in Studio.
"""
from pathlib import Path

import pytest

from nestquant_studio.paths import output_dir

# ===================================================================
# PART X: RESEARCH DATA ANALYSIS
# ===================================================================


class TestResearchAnalysis:
    def test_load_s0(self):
        from nestquant_studio.research.shared.analytics.research_analysis import ResearchAnalyzer
        analyzer = ResearchAnalyzer()
        s0_path = output_dir() / "simple_strategies" / "S0_breakout_results.json"
        if s0_path.exists():
            data = analyzer.load_s0_results(str(s0_path))
            assert data is not None
            assert "original_result" in data
        else:
            pytest.skip("S0 data not available")

    def test_load_s5_5(self):
        from nestquant_studio.research.shared.analytics.research_analysis import ResearchAnalyzer
        analyzer = ResearchAnalyzer()
        s55_path = output_dir() / "simple_strategies" / "S5_5_failure_analysis.json"
        if s55_path.exists():
            data = analyzer.load_s5_5_results(str(s55_path))
            assert data is not None
            assert "monthly_stats" in data
        else:
            pytest.skip("S5_5 data not available")

    def test_analyze_monthly_stats(self):
        from nestquant_studio.research.shared.analytics.research_analysis import ResearchAnalyzer
        analyzer = ResearchAnalyzer()
        s55_path = output_dir() / "simple_strategies" / "S5_5_failure_analysis.json"
        if s55_path.exists():
            data = analyzer.load_s5_5_results(str(s55_path))
            result = analyzer.analyze_monthly_stats(data)
            assert result.n_months > 0
            assert result.pnl_dist.count > 0
            assert result.max_dd_dist.count > 0
        else:
            pytest.skip("S5_5 data not available")

    def test_analyze_consecutive_losses(self):
        from nestquant_studio.research.shared.analytics.research_analysis import ResearchAnalyzer
        analyzer = ResearchAnalyzer()
        s55_path = output_dir() / "simple_strategies" / "S5_5_failure_analysis.json"
        if s55_path.exists():
            data = analyzer.load_s5_5_results(str(s55_path))
            result = analyzer.analyze_consecutive_losses(data)
            assert result.n_months > 0
            assert result.max_consec_losses_dist.count > 0
        else:
            pytest.skip("S5_5 data not available")

    def test_analyze_risk_scaling(self):
        from nestquant_studio.research.shared.analytics.research_analysis import ResearchAnalyzer
        analyzer = ResearchAnalyzer()
        s6_path = output_dir() / "simple_strategies" / "S6_adaptive_risk_challenge.json"
        if s6_path.exists():
            data = analyzer.load_s6_results(str(s6_path))
            result = analyzer.analyze_risk_scaling(data)
            assert len(result.risk_levels) > 0
            assert len(result.max_dd_by_risk) > 0
        else:
            pytest.skip("S6 data not available")

    def test_analyze_monte_carlo(self):
        from nestquant_studio.research.shared.analytics.research_analysis import ResearchAnalyzer
        analyzer = ResearchAnalyzer()
        s6_path = output_dir() / "simple_strategies" / "S6_adaptive_risk_challenge.json"
        if s6_path.exists():
            data = analyzer.load_s6_results(str(s6_path))
            result = analyzer.analyze_monte_carlo(data)
            assert len(result.scenarios) > 0
            assert len(result.median_max_dd) > 0
        else:
            pytest.skip("S6 data not available")


