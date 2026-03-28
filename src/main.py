"""Main CLI for monthly analysis report generator"""
import sys
import os
import argparse
from pathlib import Path
from decimal import Decimal

import yaml
from src.extractors import RentRollExtractor, T12Extractor, RentRollSummary, T12Data
from src.generators import NarrativeGenerator, FullReportGenerator

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'property_config.yaml')


def _load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f) or {}
    return {}


def _build_occupancy_analysis(rr: RentRollSummary) -> dict:
    total = rr.total_units
    occupied = rr.occupied_units
    vacant = rr.vacant_units
    pct = round(occupied / total * 100, 2) if total > 0 else 0
    return {
        'total_units': total,
        'occupied_units': occupied,
        'vacant_units': vacant,
        'physical_occupancy_pct': pct,
        'vacancy_loss': float(rr.vacancy_loss),
    }


def _build_financial_analysis(t12: T12Data) -> dict:
    months = list(t12.months.values())
    revenues = [float(m.total_income) for m in months if float(m.total_income) != 0]
    nois     = [float(m.noi) for m in months if float(m.noi) != 0]

    avg_rev = sum(revenues) / len(revenues) if revenues else 0
    avg_noi = sum(nois) / len(nois) if nois else 0

    # Simple trend: compare last 3 months average to first 3 months average
    def _trend(vals):
        if len(vals) < 6:
            return 'stable'
        first_half = sum(vals[:len(vals)//2]) / (len(vals)//2)
        second_half = sum(vals[len(vals)//2:]) / (len(vals) - len(vals)//2)
        if second_half > first_half * 1.02:
            return 'increasing'
        elif second_half < first_half * 0.98:
            return 'decreasing'
        return 'stable'

    return {
        'revenue_analysis': {
            'average_monthly_revenue': avg_rev,
            'trend': _trend(revenues),
        },
        'noi_analysis': {
            'average_noi': avg_noi,
        },
        'trends': {
            'noi': _trend(nois),
        },
    }


def _build_collections_analysis(rr: RentRollSummary) -> dict:
    delinquent_units = []
    for u in rr.units:
        if float(u.debit_balance) > 0:
            severity = (
                'High' if float(u.debit_balance) >= 5000 else
                'Medium' if float(u.debit_balance) >= 1000 else
                'Low'
            )
            delinquent_units.append({
                'unit': u.unit,
                'tenant': u.tenant,
                'debit_balance': float(u.debit_balance),
                'severity': severity,
            })

    delinquent_units.sort(key=lambda x: x['debit_balance'], reverse=True)

    total_charged = float(rr.total_charged)
    total_paid    = float(rr.total_paid)
    cr = round(total_paid / total_charged * 100, 2) if total_charged > 0 else 0

    return {
        'total_debit_balance': float(rr.debit_balances),
        'delinquent_units': delinquent_units,
        'collection_stats': {
            'total_charged': total_charged,
            'total_paid': total_paid,
            'collection_rate_pct': cr,
            'total_delinquent_units': len(delinquent_units),
        },
    }


def main():
    parser = argparse.ArgumentParser(description='Generate monthly analysis reports')
    parser.add_argument('--rent-roll',  required=True, help='Path to Rent Roll PDF')
    parser.add_argument('--financials', required=True, help='Path to T12 Financials PDF')
    parser.add_argument('--output',     required=False, default='output/report.docx', help='Output path')

    args = parser.parse_args()

    if not Path(args.rent_roll).exists():
        print(f"Error: Rent roll file not found: {args.rent_roll}")
        sys.exit(1)

    if not Path(args.financials).exists():
        print(f"Error: Financials file not found: {args.financials}")
        sys.exit(1)

    output_dir = Path(args.output).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        print("Extracting rent roll data...")
        rr = RentRollExtractor(args.rent_roll).extract()
        print(f"  ✓ {rr.total_units} total units | {rr.occupied_units} occupied | {rr.vacant_units} vacant")

        print("Extracting T12 financial data...")
        t12 = T12Extractor(args.financials).extract()
        months_with_data = sum(1 for m in t12.months.values() if float(m.total_income) != 0)
        print(f"  ✓ {len(t12.months)} months defined | {months_with_data} with income data")

        print("Loading config...")
        cfg = _load_config()

        print("Initializing narrative generator...")
        ng = NarrativeGenerator(config=cfg)
        mode = "Claude via Bedrock" if ng.use_bedrock else "template-based"
        print(f"  ✓ Narrative mode: {mode}")

        print("Building analysis...")
        occ  = _build_occupancy_analysis(rr)
        fin  = _build_financial_analysis(t12)
        col  = _build_collections_analysis(rr)
        print(f"  ✓ Occupancy: {occ['physical_occupancy_pct']}%")
        print(f"  ✓ Avg NOI: ${fin['noi_analysis']['average_noi']:,.2f}")
        print(f"  ✓ Delinquent units: {col['collection_stats']['total_delinquent_units']}")

        print(f"Generating full report → {args.output}")
        generator = FullReportGenerator(rr, t12, occ, fin, col, ng, config_path=CONFIG_PATH)
        output_path = generator.generate(args.output)

        print(f"\n✓ Report saved to: {output_path}")

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
