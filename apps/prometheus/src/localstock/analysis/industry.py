"""Vietnamese industry grouping and comparison analysis (FUND-03).

Per D-03: Vietnamese-specific industry groups (not standard ICB).
Defines 20 VN industry groups with ICB3 mapping from vnstock data.
"""

from datetime import UTC, datetime

from loguru import logger


# Vietnamese industry groups per Research section 5
VN_INDUSTRY_GROUPS: list[dict] = [
    {"group_code": "BANKING", "group_name_vi": "Ngân hàng", "group_name_en": "Banking"},
    {"group_code": "REAL_ESTATE", "group_name_vi": "Bất động sản", "group_name_en": "Real Estate"},
    {"group_code": "SECURITIES", "group_name_vi": "Chứng khoán", "group_name_en": "Securities/Brokerage"},
    {"group_code": "INSURANCE", "group_name_vi": "Bảo hiểm", "group_name_en": "Insurance"},
    {"group_code": "STEEL", "group_name_vi": "Thép", "group_name_en": "Steel"},
    {"group_code": "SEAFOOD", "group_name_vi": "Thủy sản", "group_name_en": "Seafood"},
    {"group_code": "RETAIL", "group_name_vi": "Bán lẻ", "group_name_en": "Retail"},
    {"group_code": "CONSTRUCTION", "group_name_vi": "Xây dựng", "group_name_en": "Construction"},
    {"group_code": "ENERGY", "group_name_vi": "Năng lượng", "group_name_en": "Energy/Power"},
    {"group_code": "OIL_GAS", "group_name_vi": "Dầu khí", "group_name_en": "Oil & Gas"},
    {"group_code": "TECH", "group_name_vi": "Công nghệ", "group_name_en": "Technology"},
    {"group_code": "FOOD_BEVERAGE", "group_name_vi": "Thực phẩm & Đồ uống", "group_name_en": "Food & Beverage"},
    {"group_code": "TEXTILE", "group_name_vi": "Dệt may", "group_name_en": "Textile/Garment"},
    {"group_code": "PHARMA", "group_name_vi": "Dược phẩm", "group_name_en": "Pharma/Healthcare"},
    {"group_code": "LOGISTICS", "group_name_vi": "Vận tải & Logistics", "group_name_en": "Transport/Logistics"},
    {"group_code": "RUBBER", "group_name_vi": "Cao su", "group_name_en": "Rubber/Plantation"},
    {"group_code": "FERTILIZER", "group_name_vi": "Phân bón", "group_name_en": "Fertilizer/Chemicals"},
    {"group_code": "AVIATION", "group_name_vi": "Hàng không", "group_name_en": "Aviation"},
    {"group_code": "UTILITIES", "group_name_vi": "Tiện ích", "group_name_en": "Utilities"},
    {"group_code": "OTHER", "group_name_vi": "Khác", "group_name_en": "Other"},
]


# Mapping from vnstock ICB3 Vietnamese names to VN group codes
# Primary source: stocks.industry_icb3 from Phase 1 company profiles (VCI source)
ICB_TO_VN_GROUP: dict[str, str] = {
    # Banking
    "Ngân hàng": "BANKING",
    # Real Estate
    "Bất động sản": "REAL_ESTATE",
    "Phát triển Bất động sản": "REAL_ESTATE",
    # Securities/Financial Services
    "Dịch vụ tài chính": "SECURITIES",
    "Chứng khoán": "SECURITIES",
    # Insurance
    "Bảo hiểm": "INSURANCE",
    "Bảo hiểm nhân thọ": "INSURANCE",
    "Bảo hiểm phi nhân thọ": "INSURANCE",
    # Steel
    "Thép": "STEEL",
    "Kim loại": "STEEL",
    # Seafood
    "Thủy sản": "SEAFOOD",
    # Retail
    "Bán lẻ": "RETAIL",
    "Bán lẻ chuyên dụng": "RETAIL",
    "Bán lẻ thực phẩm và thuốc": "RETAIL",
    # Construction
    "Xây dựng": "CONSTRUCTION",
    "Xây dựng và vật liệu": "CONSTRUCTION",
    "Vật liệu xây dựng": "CONSTRUCTION",
    # Energy
    "Điện": "ENERGY",
    "Điện lực": "ENERGY",
    "Năng lượng": "ENERGY",
    "Năng lượng tái tạo": "ENERGY",
    # Oil & Gas
    "Dầu khí": "OIL_GAS",
    "Dầu và khí đốt": "OIL_GAS",
    # Technology
    "Công nghệ thông tin": "TECH",
    "Công nghệ": "TECH",
    "Phần mềm": "TECH",
    "Phần mềm và dịch vụ máy tính": "TECH",
    # Food & Beverage
    "Thực phẩm": "FOOD_BEVERAGE",
    "Đồ uống": "FOOD_BEVERAGE",
    "Thực phẩm và đồ uống": "FOOD_BEVERAGE",
    "Sản xuất thực phẩm": "FOOD_BEVERAGE",
    # Textile
    "Dệt may": "TEXTILE",
    "Hàng cá nhân": "TEXTILE",
    "Hàng cá nhân và gia dụng": "TEXTILE",
    # Pharma
    "Dược phẩm": "PHARMA",
    "Y tế": "PHARMA",
    "Dược phẩm và công nghệ sinh học": "PHARMA",
    "Thiết bị và dịch vụ y tế": "PHARMA",
    # Logistics
    "Vận tải": "LOGISTICS",
    "Logistics": "LOGISTICS",
    "Giao thông vận tải": "LOGISTICS",
    "Vận tải biển": "LOGISTICS",
    # Rubber
    "Cao su": "RUBBER",
    "Nông nghiệp": "RUBBER",
    "Lâm nghiệp và giấy": "RUBBER",
    # Fertilizer/Chemicals
    "Hóa chất": "FERTILIZER",
    "Phân bón": "FERTILIZER",
    # Aviation
    "Hàng không": "AVIATION",
    "Du lịch và giải trí": "AVIATION",
    # Utilities
    "Tiện ích": "UTILITIES",
    "Gas, nước và tiện ích đa dụng": "UTILITIES",
    "Nước": "UTILITIES",
}


def map_icb_to_group(icb_name: str | None) -> str:
    """Map an ICB3 Vietnamese name to a VN industry group code.

    Args:
        icb_name: ICB3 industry name from stocks.industry_icb3 (Vietnamese).

    Returns:
        VN group code (e.g., 'BANKING'). Falls back to 'OTHER' if unmapped or None.
    """
    if icb_name is None:
        return "OTHER"
    return ICB_TO_VN_GROUP.get(icb_name, "OTHER")


class IndustryAnalyzer:
    """Manages VN industry groups, stock mapping, and average computation.

    Per D-03: Vietnamese-specific groupings, not standard international ICB.
    """

    def compute_industry_averages(
        self,
        group_code: str,
        year: int,
        period: str,
        ratios: list[dict],
    ) -> dict:
        """Compute average financial ratios for an industry group (FUND-03).

        Excludes None values when computing each average.

        Args:
            group_code: Industry group code (e.g., 'BANKING').
            year: Fiscal year.
            period: 'Q1'..'Q4' or 'TTM'.
            ratios: List of dicts, each with ratio keys from FundamentalAnalyzer.

        Returns:
            Dict matching IndustryAverage model columns.
        """
        if not ratios:
            return {
                "group_code": group_code,
                "year": year,
                "period": period,
                "avg_pe": None,
                "avg_pb": None,
                "avg_roe": None,
                "avg_roa": None,
                "avg_de": None,
                "avg_revenue_growth_yoy": None,
                "avg_profit_growth_yoy": None,
                "stock_count": 0,
                "computed_at": datetime.now(UTC),
            }

        def _avg(key: str) -> float | None:
            vals = [r[key] for r in ratios if r.get(key) is not None]
            return round(sum(vals) / len(vals), 2) if vals else None

        return {
            "group_code": group_code,
            "year": year,
            "period": period,
            "avg_pe": _avg("pe_ratio"),
            "avg_pb": _avg("pb_ratio"),
            "avg_roe": _avg("roe"),
            "avg_roa": _avg("roa"),
            "avg_de": _avg("de_ratio"),
            "avg_revenue_growth_yoy": _avg("revenue_yoy"),
            "avg_profit_growth_yoy": _avg("profit_yoy"),
            "stock_count": len(ratios),
            "computed_at": datetime.now(UTC),
        }

    def get_group_definitions(self) -> list[dict]:
        """Return VN industry group definitions for DB seeding.

        Returns:
            List of dicts ready for IndustryRepository.upsert_groups().
        """
        return VN_INDUSTRY_GROUPS.copy()
