"""Financial analysis"""
from decimal import Decimal
from typing import Dict, Any, List
from src.models import T12FinancialData, MonthlyFinancials


class FinancialAnalyzer:
    """Analyze financial metrics"""

    @staticmethod
    def analyze(t12_data: T12FinancialData) -> Dict[str, Any]:
        """Perform financial analysis"""
        months_list = sorted(t12_data.months.keys())

        return {
            'revenue_analysis': FinancialAnalyzer._analyze_revenue(t12_data, months_list),
            'expense_analysis': FinancialAnalyzer._analyze_expenses(t12_data, months_list),
            'noi_analysis': FinancialAnalyzer._analyze_noi(t12_data, months_list),
            'rent_growth': FinancialAnalyzer._analyze_rent_growth(t12_data, months_list),
            'trends': FinancialAnalyzer._identify_trends(t12_data, months_list),
        }

    @staticmethod
    def _analyze_revenue(t12_data: T12FinancialData, months_list: List[str]) -> Dict[str, Any]:
        """Analyze revenue trends"""
        monthly_totals = []
        rental_income_list = []
        other_income_list = []

        for month in months_list:
            monthly = t12_data.months[month]
            monthly_totals.append({
                'month': month,
                'total': monthly.total_income,
                'rental': sum(monthly.rental_income.values()),
                'other': sum(monthly.other_income.values()),
            })
            rental_income_list.append(sum(monthly.rental_income.values()))
            other_income_list.append(sum(monthly.other_income.values()))

        # Calculate trends
        revenue_trend = 'stable'
        if len(monthly_totals) >= 3:
            recent_avg = Decimal(sum(t['total'] for t in monthly_totals[-3:])) / Decimal(3)
            earlier_avg = Decimal(sum(t['total'] for t in monthly_totals[:3])) / Decimal(3)
            if recent_avg > earlier_avg:
                revenue_trend = 'increasing'
            elif recent_avg < earlier_avg:
                revenue_trend = 'decreasing'

        return {
            'monthly_totals': monthly_totals,
            'average_monthly_revenue': sum(r['total'] for r in monthly_totals) / len(monthly_totals) if monthly_totals else Decimal('0'),
            'max_month': max(monthly_totals, key=lambda x: x['total']) if monthly_totals else None,
            'min_month': min(monthly_totals, key=lambda x: x['total']) if monthly_totals else None,
            'trend': revenue_trend,
            'rental_income_avg': sum(rental_income_list) / len(rental_income_list) if rental_income_list else Decimal('0'),
            'other_income_avg': sum(other_income_list) / len(other_income_list) if other_income_list else Decimal('0'),
        }

    @staticmethod
    def _analyze_expenses(t12_data: T12FinancialData, months_list: List[str]) -> Dict[str, Any]:
        """Analyze expense trends by category"""
        expense_categories = {
            'administrative': [],
            'marketing': [],
            'payroll': [],
            'repairs': [],
            'contract_services': [],
            'utilities': [],
            'insurance_taxes': [],
            'capital': [],
        }

        for month in months_list:
            monthly = t12_data.months[month]
            expense_categories['administrative'].append(sum(monthly.administrative_expenses.values()))
            expense_categories['marketing'].append(sum(monthly.marketing_expenses.values()))
            expense_categories['payroll'].append(sum(monthly.payroll_expenses.values()))
            expense_categories['repairs'].append(sum(monthly.repairs_maintenance.values()))
            expense_categories['contract_services'].append(sum(monthly.contract_services.values()))
            expense_categories['utilities'].append(sum(monthly.utilities_expenses.values()))
            expense_categories['insurance_taxes'].append(sum(monthly.insurance_taxes.values()))
            expense_categories['capital'].append(sum(monthly.capital_expenses.values()))

        # Calculate averages
        category_averages = {}
        for category, values in expense_categories.items():
            if values:
                category_averages[category] = sum(values) / len(values)

        total_expenses = sum(
            sum(t12_data.months[m].administrative_expenses.values()) +
            sum(t12_data.months[m].marketing_expenses.values()) +
            sum(t12_data.months[m].payroll_expenses.values()) +
            sum(t12_data.months[m].repairs_maintenance.values()) +
            sum(t12_data.months[m].contract_services.values()) +
            sum(t12_data.months[m].utilities_expenses.values()) +
            sum(t12_data.months[m].insurance_taxes.values()) +
            sum(t12_data.months[m].capital_expenses.values())
            for m in months_list
        )

        return {
            'category_averages': category_averages,
            'total_annual_expenses': total_expenses,
            'highest_expense_category': max(category_averages, key=category_averages.get) if category_averages else None,
        }

    @staticmethod
    def _analyze_noi(t12_data: T12FinancialData, months_list: List[str]) -> Dict[str, Any]:
        """Analyze NOI trends"""
        noi_values = [t12_data.months[m].noi for m in months_list]

        return {
            'monthly_noi': [{'month': m, 'noi': t12_data.months[m].noi} for m in months_list],
            'average_noi': sum(noi_values) / len(noi_values) if noi_values else Decimal('0'),
            'max_noi_month': max(months_list, key=lambda m: t12_data.months[m].noi) if months_list else None,
            'min_noi_month': min(months_list, key=lambda m: t12_data.months[m].noi) if months_list else None,
        }

    @staticmethod
    def _analyze_rent_growth(t12_data: T12FinancialData, months_list: List[str]) -> Dict[str, Any]:
        """Analyze rent growth percentage"""
        rental_income_values = [
            sum(t12_data.months[m].rental_income.values()) for m in months_list
        ]

        growth_rates = []
        for i in range(1, len(rental_income_values)):
            prev = rental_income_values[i - 1]
            current = rental_income_values[i]
            if prev != 0:
                growth = ((current - prev) / prev * Decimal('100')).quantize(Decimal('0.01'))
                growth_rates.append({
                    'month': months_list[i],
                    'growth_pct': growth,
                })

        return {
            'monthly_growth_rates': growth_rates,
            'average_growth_pct': sum(r['growth_pct'] for r in growth_rates) / len(growth_rates) if growth_rates else Decimal('0'),
        }

    @staticmethod
    def _identify_trends(t12_data: T12FinancialData, months_list: List[str]) -> Dict[str, str]:
        """Identify overall trends"""
        if not months_list or len(months_list) < 2:
            return {'note': 'Insufficient data for trend analysis'}

        latest_month = t12_data.months[months_list[-1]]
        earlier_month = t12_data.months[months_list[0]]

        trends = {}

        # Revenue trend
        if latest_month.total_income > earlier_month.total_income:
            trends['revenue'] = 'increasing'
        elif latest_month.total_income < earlier_month.total_income:
            trends['revenue'] = 'decreasing'
        else:
            trends['revenue'] = 'stable'

        # Expense trend
        latest_expenses = sum(sum(getattr(latest_month, f'{cat}_expenses', {}).values())
                               for cat in ['administrative', 'marketing', 'payroll', 'repairs_maintenance', 'contract_services', 'utilities_expenses', 'insurance_taxes'])
        earlier_expenses = sum(sum(getattr(earlier_month, f'{cat}_expenses', {}).values())
                                for cat in ['administrative', 'marketing', 'payroll', 'repairs_maintenance', 'contract_services', 'utilities_expenses', 'insurance_taxes'])

        if latest_expenses > earlier_expenses:
            trends['expenses'] = 'increasing'
        elif latest_expenses < earlier_expenses:
            trends['expenses'] = 'decreasing'
        else:
            trends['expenses'] = 'stable'

        # NOI trend
        if latest_month.noi > earlier_month.noi:
            trends['noi'] = 'improving'
        elif latest_month.noi < earlier_month.noi:
            trends['noi'] = 'declining'
        else:
            trends['noi'] = 'stable'

        return trends
