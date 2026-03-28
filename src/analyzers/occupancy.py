"""Occupancy analysis"""
from decimal import Decimal
from typing import Dict, Any
from src.models import RentRollData


class OccupancyAnalyzer:
    """Analyze occupancy metrics"""

    @staticmethod
    def analyze(rent_roll: RentRollData) -> Dict[str, Any]:
        """Perform occupancy analysis"""
        return {
            'total_units': rent_roll.total_units,
            'occupied_units': rent_roll.occupied_units,
            'vacant_units': rent_roll.vacant_units,
            'physical_occupancy_pct': OccupancyAnalyzer._calc_occupancy_pct(
                rent_roll.occupied_units, rent_roll.total_units
            ),
            'vacancy_loss': rent_roll.vacancy_loss,
            'vacant_units_detail': OccupancyAnalyzer._get_vacant_units(rent_roll),
            'long_term_vacant': OccupancyAnalyzer._identify_long_term_vacant(rent_roll),
            'model_units': OccupancyAnalyzer._count_model_units(rent_roll),
        }

    @staticmethod
    def _calc_occupancy_pct(occupied: int, total: int) -> Decimal:
        """Calculate occupancy percentage"""
        if total == 0:
            return Decimal('0')
        return (Decimal(occupied) / Decimal(total) * Decimal('100')).quantize(Decimal('0.01'))

    @staticmethod
    def _get_vacant_units(rent_roll: RentRollData) -> list:
        """Get list of vacant units"""
        return [u.unit_number for u in rent_roll.units if u.status == 'vacant']

    @staticmethod
    def _identify_long_term_vacant(rent_roll: RentRollData) -> list:
        """Identify long-term vacant units (15+ days)"""
        # This would require move-out date tracking which isn't in rent roll
        # Return as informational note for now
        return {
            'threshold_days': 15,
            'note': 'Long-term vacancy requires additional data beyond rent roll'
        }

    @staticmethod
    def _count_model_units(rent_roll: RentRollData) -> int:
        """Count model/non-revenue units"""
        # Look for units marked as model or non-revenue
        return sum(1 for u in rent_roll.units if u.tenant_name and 'model' in u.tenant_name.lower())
