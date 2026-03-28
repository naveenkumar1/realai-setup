from pydantic import BaseModel
from decimal import Decimal
from typing import Dict, Optional


class MonthlyFinancials(BaseModel):
    """Financial data for a single month"""
    month: str  # e.g., "JAN 25", "DEC 25"
    rental_income: Dict[str, Decimal] = {}  # Gross Potential, Vacancy Loss, Net, etc.
    other_income: Dict[str, Decimal] = {}  # Late fees, parking, utilities, etc.
    total_income: Decimal = Decimal('0')
    administrative_expenses: Dict[str, Decimal] = {}
    marketing_expenses: Dict[str, Decimal] = {}
    payroll_expenses: Dict[str, Decimal] = {}
    repairs_maintenance: Dict[str, Decimal] = {}
    contract_services: Dict[str, Decimal] = {}
    utilities_expenses: Dict[str, Decimal] = {}
    insurance_taxes: Dict[str, Decimal] = {}
    capital_expenses: Dict[str, Decimal] = {}
    total_expenses: Decimal = Decimal('0')
    noi: Decimal = Decimal('0')
    debt_service: Decimal = Decimal('0')
    net_income: Decimal = Decimal('0')

    class Config:
        json_encoders = {Decimal: str}


class T12FinancialData(BaseModel):
    """12-month financial data extracted from T12 PDF"""
    property_name: str
    year: int
    months: Dict[str, MonthlyFinancials] = {}  # Keyed by month abbreviation
    annual_totals: Optional[MonthlyFinancials] = None

    class Config:
        json_encoders = {Decimal: str}
