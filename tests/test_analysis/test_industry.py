"""Tests for IndustryAnalyzer — VN industry groups and comparison (FUND-03)."""

import pytest

from localstock.analysis.industry import (
    ICB_TO_VN_GROUP,
    VN_INDUSTRY_GROUPS,
    IndustryAnalyzer,
    map_icb_to_group,
)


class TestVNIndustryGroups:
    def test_has_20_groups(self):
        assert len(VN_INDUSTRY_GROUPS) == 20

    def test_each_group_has_required_fields(self):
        for group in VN_INDUSTRY_GROUPS:
            assert "group_code" in group
            assert "group_name_vi" in group
            assert "group_name_en" in group

    def test_banking_group_exists(self):
        codes = [g["group_code"] for g in VN_INDUSTRY_GROUPS]
        assert "BANKING" in codes

    def test_other_group_exists(self):
        codes = [g["group_code"] for g in VN_INDUSTRY_GROUPS]
        assert "OTHER" in codes


class TestICBMapping:
    def test_ngan_hang_to_banking(self):
        assert ICB_TO_VN_GROUP["Ngân hàng"] == "BANKING"

    def test_bat_dong_san_to_real_estate(self):
        assert ICB_TO_VN_GROUP["Bất động sản"] == "REAL_ESTATE"

    def test_map_icb_to_group_known(self):
        assert map_icb_to_group("Ngân hàng") == "BANKING"

    def test_map_icb_to_group_none(self):
        assert map_icb_to_group(None) == "OTHER"

    def test_map_icb_to_group_unknown(self):
        assert map_icb_to_group("Some Unknown Industry") == "OTHER"


class TestComputeIndustryAverages:
    def test_averages_ratios(self):
        analyzer = IndustryAnalyzer()
        ratios = [
            {"pe_ratio": 10.0, "pb_ratio": 2.0, "roe": 15.0, "roa": 1.5, "de_ratio": 8.0, "revenue_yoy": 10.0, "profit_yoy": 12.0},
            {"pe_ratio": 12.0, "pb_ratio": 1.8, "roe": 18.0, "roa": 1.8, "de_ratio": 9.0, "revenue_yoy": 15.0, "profit_yoy": 8.0},
            {"pe_ratio": 8.0, "pb_ratio": 2.5, "roe": 12.0, "roa": 1.2, "de_ratio": 7.0, "revenue_yoy": 8.0, "profit_yoy": 20.0},
        ]
        result = analyzer.compute_industry_averages("BANKING", 2024, "Q3", ratios)
        assert result["avg_pe"] == pytest.approx(10.0, rel=0.01)
        assert result["avg_pb"] == pytest.approx(2.1, rel=0.01)
        assert result["avg_roe"] == pytest.approx(15.0, rel=0.01)
        assert result["stock_count"] == 3

    def test_excludes_none_from_average(self):
        analyzer = IndustryAnalyzer()
        ratios = [
            {"pe_ratio": 10.0, "pb_ratio": None, "roe": 15.0, "roa": 1.5, "de_ratio": 8.0, "revenue_yoy": None, "profit_yoy": None},
            {"pe_ratio": 12.0, "pb_ratio": 2.0, "roe": None, "roa": 1.8, "de_ratio": 9.0, "revenue_yoy": None, "profit_yoy": None},
        ]
        result = analyzer.compute_industry_averages("BANKING", 2024, "Q3", ratios)
        assert result["avg_pe"] == pytest.approx(11.0, rel=0.01)
        assert result["avg_pb"] == pytest.approx(2.0, rel=0.01)
        assert result["avg_roe"] == pytest.approx(15.0, rel=0.01)
        assert result["stock_count"] == 2

    def test_empty_ratios(self):
        analyzer = IndustryAnalyzer()
        result = analyzer.compute_industry_averages("BANKING", 2024, "Q3", [])
        assert result["stock_count"] == 0
        assert result["avg_pe"] is None
