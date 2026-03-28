"""Main CLI for monthly analysis report generator"""
import sys
import argparse
from pathlib import Path
from src.extractors import RentRollExtractor, T12Extractor
from src.analyzers import OccupancyAnalyzer, FinancialAnalyzer, CollectionsAnalyzer
from src.generators.template_report_generator import TemplateReportGenerator


def main():
    parser = argparse.ArgumentParser(description='Generate monthly analysis reports')
    parser.add_argument('--rent-roll', required=True, help='Path to Rent Roll PDF')
    parser.add_argument('--financials', required=True, help='Path to T12 Financials PDF')
    parser.add_argument('--output', required=False, default='output/report.docx', help='Output path')

    args = parser.parse_args()

    # Validate inputs
    if not Path(args.rent_roll).exists():
        print(f"Error: Rent roll file not found: {args.rent_roll}")
        sys.exit(1)

    if not Path(args.financials).exists():
        print(f"Error: Financials file not found: {args.financials}")
        sys.exit(1)

    # Create output directory
    output_dir = Path(args.output).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        print("Extracting rent roll data...")
        rent_roll_extractor = RentRollExtractor(args.rent_roll)
        rent_roll_data = rent_roll_extractor.extract()
        print(f"  ✓ Extracted {len(rent_roll_data.units)} units")

        print("Extracting T12 financial data...")
        t12_extractor = T12Extractor(args.financials)
        t12_data = t12_extractor.extract()
        print(f"  ✓ Extracted {len(t12_data.months)} months of financials")

        print("Analyzing occupancy metrics...")
        occupancy_analysis = OccupancyAnalyzer.analyze(rent_roll_data)
        print(f"  ✓ Occupancy: {occupancy_analysis['physical_occupancy_pct']}%")

        print("Analyzing financial metrics...")
        financial_analysis = FinancialAnalyzer.analyze(t12_data)
        print(f"  ✓ Average NOI: ${financial_analysis['noi_analysis']['average_noi']:,.2f}")

        print("Analyzing collections metrics...")
        collections_analysis = CollectionsAnalyzer.analyze(rent_roll_data)
        print(f"  ✓ Delinquent units: {collections_analysis['collection_stats']['total_delinquent_units']}")

        print(f"Generating report to {args.output}...")
        generator = TemplateReportGenerator(
            rent_roll_data, t12_data,
            occupancy_analysis, financial_analysis, collections_analysis
        )
        output_path = generator.generate(args.output)
        print(f"  ✓ Report generated successfully!")
        print(f"  ✓ Saved to: {output_path}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
