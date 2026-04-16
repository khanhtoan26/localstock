"""MACRO_SECTOR_IMPACT — rules-based mapping of macro conditions to sector impacts.

Per Research MACR-02: Deterministic domain knowledge, not LLM.
8 macro conditions × 20 VN industry sectors → impact multiplier in [-1.0, +1.0].

Positive = favorable for sector, Negative = unfavorable.
OTHER always 0.0 (no specific macro sensitivity).

[ASSUMED] — These multipliers are reasonable starting points based on Vietnamese
market domain knowledge. Should be calibrated over time with actual market data.
"""


# 8 conditions × 20 sectors
# Values from Research §Macro-to-Sector Impact Scoring table + filled gaps
MACRO_SECTOR_IMPACT: dict[str, dict[str, float]] = {
    "interest_rate_rising": {
        "BANKING": 0.7,        # Wider NIM
        "REAL_ESTATE": -0.8,   # Higher borrowing costs
        "SECURITIES": -0.6,    # Lower trading volume
        "INSURANCE": 0.3,      # Better fixed-income returns
        "STEEL": -0.4,         # Higher financing costs
        "SEAFOOD": -0.2,       # Slight financing pressure
        "RETAIL": -0.3,        # Consumer credit tightens
        "CONSTRUCTION": -0.5,  # Project financing harder
        "ENERGY": 0.0,         # Regulated, low sensitivity
        "OIL_GAS": -0.2,       # Slight financing pressure
        "TECH": -0.1,          # Low debt sector
        "FOOD_BEVERAGE": -0.1, # Defensive, low sensitivity
        "TEXTILE": -0.3,       # Export financing costs
        "PHARMA": -0.1,        # Defensive sector
        "LOGISTICS": -0.2,     # Fleet financing costs
        "RUBBER": -0.3,        # Plantation financing
        "FERTILIZER": -0.2,    # Working capital costs
        "AVIATION": -0.5,      # Heavy debt sector
        "UTILITIES": 0.0,      # Regulated pricing
        "OTHER": 0.0,
    },
    "interest_rate_falling": {
        "BANKING": -0.3,       # NIM compression
        "REAL_ESTATE": 0.8,    # Cheaper mortgages
        "SECURITIES": 0.6,     # More trading activity
        "INSURANCE": -0.2,     # Lower fixed-income returns
        "STEEL": 0.3,          # Cheaper financing
        "SEAFOOD": 0.2,        # Easier credit
        "RETAIL": 0.3,         # Consumer spending up
        "CONSTRUCTION": 0.5,   # Cheaper project finance
        "ENERGY": 0.0,         # Regulated
        "OIL_GAS": 0.2,        # Easier financing
        "TECH": 0.1,           # Growth stocks benefit
        "FOOD_BEVERAGE": 0.1,  # Slight consumer boost
        "TEXTILE": 0.2,        # Cheaper working capital
        "PHARMA": 0.1,         # Slight benefit
        "LOGISTICS": 0.2,      # Cheaper fleet finance
        "RUBBER": 0.2,         # Cheaper plantation loans
        "FERTILIZER": 0.2,     # Working capital cheaper
        "AVIATION": 0.5,       # Debt relief
        "UTILITIES": 0.0,      # Regulated
        "OTHER": 0.0,
    },
    "vnd_weakening": {
        "BANKING": 0.2,        # FX trading gains
        "REAL_ESTATE": -0.2,   # Import materials costlier
        "SECURITIES": -0.1,    # Capital outflow risk
        "INSURANCE": -0.1,     # Foreign claims costlier
        "STEEL": -0.3,         # Import raw materials
        "SEAFOOD": 0.6,        # Export competitive advantage
        "RETAIL": -0.3,        # Import goods costlier
        "CONSTRUCTION": -0.2,  # Import materials costlier
        "ENERGY": -0.3,        # Import fuel costlier
        "OIL_GAS": -0.4,       # Import cost pressure
        "TECH": 0.2,           # Export software revenue
        "FOOD_BEVERAGE": 0.1,  # Mixed — some export
        "TEXTILE": 0.5,        # Major exporter
        "PHARMA": -0.3,        # Import raw materials
        "LOGISTICS": 0.1,      # Some export logistics
        "RUBBER": 0.4,         # Export commodity
        "FERTILIZER": -0.2,    # Import raw materials
        "AVIATION": -0.4,      # USD-denominated costs
        "UTILITIES": -0.1,     # Some import fuel
        "OTHER": 0.0,
    },
    "vnd_strengthening": {
        "BANKING": -0.2,       # FX trading losses
        "REAL_ESTATE": 0.2,    # Cheaper imports
        "SECURITIES": 0.1,     # Capital inflow
        "INSURANCE": 0.1,      # Cheaper foreign claims
        "STEEL": 0.3,          # Cheaper raw materials
        "SEAFOOD": -0.4,       # Less competitive exports
        "RETAIL": 0.3,         # Cheaper imports
        "CONSTRUCTION": 0.2,   # Cheaper materials
        "ENERGY": 0.2,         # Cheaper fuel imports
        "OIL_GAS": 0.3,        # Cheaper imports
        "TECH": -0.1,          # Export revenue lower
        "FOOD_BEVERAGE": 0.0,  # Mixed
        "TEXTILE": -0.3,       # Less competitive exports
        "PHARMA": 0.2,         # Cheaper raw materials
        "LOGISTICS": -0.1,     # Mixed
        "RUBBER": -0.3,        # Export commodity hurt
        "FERTILIZER": 0.2,     # Cheaper imports
        "AVIATION": 0.3,       # USD costs cheaper
        "UTILITIES": 0.1,      # Cheaper fuel
        "OTHER": 0.0,
    },
    "cpi_rising": {
        "BANKING": 0.3,        # Rate hike expectations
        "REAL_ESTATE": -0.5,   # Demand drops
        "SECURITIES": -0.3,    # Risk-off sentiment
        "INSURANCE": 0.1,      # Premium adjustments
        "STEEL": -0.2,         # Input cost pressure
        "SEAFOOD": 0.1,        # Food price pass-through
        "RETAIL": -0.4,        # Consumer spending drops
        "CONSTRUCTION": -0.3,  # Higher material costs
        "ENERGY": 0.1,         # Energy prices up
        "OIL_GAS": 0.2,        # Oil price correlation
        "TECH": 0.0,           # Low sensitivity
        "FOOD_BEVERAGE": 0.3,  # Can pass through costs
        "TEXTILE": -0.2,       # Input costs up
        "PHARMA": 0.1,         # Defensive/essential
        "LOGISTICS": -0.2,     # Fuel costs up
        "RUBBER": 0.0,         # Mixed
        "FERTILIZER": 0.1,     # Commodity price up
        "AVIATION": -0.4,      # Fuel and operational costs
        "UTILITIES": 0.1,      # Can pass costs
        "OTHER": 0.0,
    },
    "cpi_falling": {
        "BANKING": -0.2,       # Rate cut expectations
        "REAL_ESTATE": 0.3,    # Demand recovery
        "SECURITIES": 0.2,     # Risk-on sentiment
        "INSURANCE": 0.0,      # Neutral
        "STEEL": 0.1,          # Input cost relief
        "SEAFOOD": -0.1,       # Food prices lower
        "RETAIL": 0.4,         # Consumer spending up
        "CONSTRUCTION": 0.2,   # Lower material costs
        "ENERGY": -0.1,        # Energy prices down
        "OIL_GAS": -0.2,       # Oil price correlation
        "TECH": 0.0,           # Low sensitivity
        "FOOD_BEVERAGE": -0.1, # Revenue pressure
        "TEXTILE": 0.1,        # Input cost relief
        "PHARMA": 0.0,         # Stable
        "LOGISTICS": 0.2,      # Fuel costs down
        "RUBBER": 0.0,         # Mixed
        "FERTILIZER": -0.1,    # Commodity prices down
        "AVIATION": 0.3,       # Fuel cost relief
        "UTILITIES": 0.0,      # Regulated
        "OTHER": 0.0,
    },
    "gdp_growing": {
        "BANKING": 0.5,        # Credit growth
        "REAL_ESTATE": 0.6,    # Demand expansion
        "SECURITIES": 0.5,     # Market optimism
        "INSURANCE": 0.3,      # More policies sold
        "STEEL": 0.5,          # Construction demand
        "SEAFOOD": 0.3,        # Domestic + export demand
        "RETAIL": 0.5,         # Consumer confidence
        "CONSTRUCTION": 0.7,   # Infrastructure investment
        "ENERGY": 0.3,         # Industrial demand
        "OIL_GAS": 0.3,        # Energy demand
        "TECH": 0.4,           # Business investment
        "FOOD_BEVERAGE": 0.3,  # Consumer spending
        "TEXTILE": 0.3,        # Export + domestic
        "PHARMA": 0.2,         # Healthcare spending
        "LOGISTICS": 0.4,      # Trade volume
        "RUBBER": 0.3,         # Industrial demand
        "FERTILIZER": 0.2,     # Agricultural cycle
        "AVIATION": 0.4,       # Travel demand
        "UTILITIES": 0.2,      # Stable demand growth
        "OTHER": 0.0,
    },
    "gdp_slowing": {
        "BANKING": -0.4,       # NPL risk rises
        "REAL_ESTATE": -0.6,   # Demand contraction
        "SECURITIES": -0.5,    # Market pessimism
        "INSURANCE": -0.2,     # Fewer new policies
        "STEEL": -0.5,         # Construction slowdown
        "SEAFOOD": -0.2,       # Demand softens
        "RETAIL": -0.4,        # Consumer pullback
        "CONSTRUCTION": -0.6,  # Investment cuts
        "ENERGY": -0.2,        # Lower industrial demand
        "OIL_GAS": -0.2,       # Lower demand
        "TECH": -0.2,          # Capex cuts
        "FOOD_BEVERAGE": -0.1, # Defensive, essential
        "TEXTILE": -0.3,       # Export demand drops
        "PHARMA": -0.1,        # Defensive/essential
        "LOGISTICS": -0.3,     # Trade volume drops
        "RUBBER": -0.3,        # Industrial demand falls
        "FERTILIZER": -0.1,    # Agricultural stable
        "AVIATION": -0.4,      # Travel cuts
        "UTILITIES": -0.1,     # Essential services
        "OTHER": 0.0,
    },
}

# Mapping from macro condition dict values to impact keys
_CONDITION_TO_KEY: dict[str, dict[str, str]] = {
    "interest_rate": {"rising": "interest_rate_rising", "falling": "interest_rate_falling"},
    "exchange_rate": {"weakening": "vnd_weakening", "strengthening": "vnd_strengthening"},
    "cpi": {"rising": "cpi_rising", "falling": "cpi_falling"},
    "gdp": {"growing": "gdp_growing", "slowing": "gdp_slowing"},
}


def get_macro_impact(
    sector_code: str, macro_conditions: dict[str, str]
) -> float:
    """Compute aggregate macro impact for a sector given current conditions.

    Sums impact multipliers across all active macro conditions for the sector,
    then clamps to [-1.0, +1.0].

    Args:
        sector_code: VN industry group code (e.g., 'BANKING').
        macro_conditions: Dict of active conditions.
            Keys: 'interest_rate', 'exchange_rate', 'cpi', 'gdp'.
            Values: trend direction (e.g., 'rising', 'falling', 'weakening').

    Returns:
        Aggregate impact in [-1.0, +1.0]. 0.0 for unknown sector or no conditions.
    """
    if not macro_conditions or sector_code == "OTHER":
        return 0.0

    total_impact = 0.0

    for indicator_type, trend in macro_conditions.items():
        # Map condition to impact key
        key_map = _CONDITION_TO_KEY.get(indicator_type)
        if key_map is None:
            continue

        impact_key = key_map.get(trend)
        if impact_key is None:
            continue  # "stable" or unknown trend → no impact

        sector_impacts = MACRO_SECTOR_IMPACT.get(impact_key, {})
        total_impact += sector_impacts.get(sector_code, 0.0)

    # Clamp to [-1.0, +1.0]
    return max(-1.0, min(1.0, total_impact))
