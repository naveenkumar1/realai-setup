"""Collections and accounts receivable analysis"""
from decimal import Decimal
from typing import Dict, Any, List
from src.models import RentRollData


class CollectionsAnalyzer:
    """Analyze collections and delinquency"""

    @staticmethod
    def analyze(rent_roll: RentRollData) -> Dict[str, Any]:
        """Perform collections analysis"""
        return {
            'total_debit_balance': rent_roll.total_debit_balance,
            'total_credit_balance': rent_roll.total_credit_balance,
            'delinquent_units': CollectionsAnalyzer._get_delinquent_units(rent_roll),
            'delinquency_summary': CollectionsAnalyzer._summarize_delinquency(rent_roll),
            'collection_stats': CollectionsAnalyzer._calculate_collection_stats(rent_roll),
        }

    @staticmethod
    def _get_delinquent_units(rent_roll: RentRollData) -> List[Dict[str, Any]]:
        """Get list of delinquent units (units with debit balance)"""
        delinquent = []
        for unit in rent_roll.units:
            if unit.debit_balance > 0:
                delinquent.append({
                    'unit_number': unit.unit_number,
                    'tenant_name': unit.tenant_name or 'N/A',
                    'debit_balance': unit.debit_balance,
                    'status': unit.status,
                })
        return sorted(delinquent, key=lambda x: x['debit_balance'], reverse=True)

    @staticmethod
    def _summarize_delinquency(rent_roll: RentRollData) -> Dict[str, Any]:
        """Summarize delinquency by severity"""
        # Note: Rent roll doesn't have aging detail, so we estimate based on balance amount
        severity_levels = {
            'under_1k': {'count': 0, 'total': Decimal('0')},
            '1k_to_5k': {'count': 0, 'total': Decimal('0')},
            '5k_plus': {'count': 0, 'total': Decimal('0')},
        }

        for unit in rent_roll.units:
            if unit.debit_balance > 0:
                if unit.debit_balance < Decimal('1000'):
                    severity_levels['under_1k']['count'] += 1
                    severity_levels['under_1k']['total'] += unit.debit_balance
                elif unit.debit_balance < Decimal('5000'):
                    severity_levels['1k_to_5k']['count'] += 1
                    severity_levels['1k_to_5k']['total'] += unit.debit_balance
                else:
                    severity_levels['5k_plus']['count'] += 1
                    severity_levels['5k_plus']['total'] += unit.debit_balance

        return severity_levels

    @staticmethod
    def _calculate_collection_stats(rent_roll: RentRollData) -> Dict[str, Any]:
        """Calculate collection statistics"""
        total_charged = sum(u.rent_charges for u in rent_roll.units)
        total_paid = sum(u.total_paid for u in rent_roll.units)
        collection_rate = Decimal('0')

        if total_charged > 0:
            collection_rate = (total_paid / total_charged * Decimal('100')).quantize(Decimal('0.01'))

        return {
            'total_charged': total_charged,
            'total_paid': total_paid,
            'collection_rate_pct': collection_rate,
            'total_delinquent_units': sum(1 for u in rent_roll.units if u.debit_balance > 0),
            'total_units_occupied': sum(1 for u in rent_roll.units if u.status == 'occupied'),
        }
