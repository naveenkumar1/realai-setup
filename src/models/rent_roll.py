from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import date
from typing import List, Optional


class UnitData(BaseModel):
    """Individual unit data from rent roll"""
    unit_number: str
    tenant_name: Optional[str] = None
    sq_ft: int
    market_rent: Decimal
    actual_rent: Decimal
    status: str  # 'occupied' or 'vacant'
    deposit_held: Decimal = Decimal('0')
    prior_balance: Decimal = Decimal('0')
    rent_charges: Decimal = Decimal('0')
    misc_charges: Decimal = Decimal('0')
    credits: Decimal = Decimal('0')
    total_charged: Decimal = Decimal('0')
    total_paid: Decimal = Decimal('0')
    debit_balance: Decimal = Decimal('0')
    credit_balance: Decimal = Decimal('0')

    class Config:
        json_encoders = {Decimal: str}


class RentRollData(BaseModel):
    """Complete rent roll data extracted from PDF"""
    property_name: str
    report_date: date
    total_units: int
    occupied_units: int
    vacant_units: int
    market_rent: Decimal
    actual_rent: Decimal
    vacancy_loss: Decimal
    loss_to_lease: Decimal
    total_sq_ft: int = 0
    total_deposits: Decimal = Decimal('0')
    total_prior_balance: Decimal = Decimal('0')
    total_debit_balance: Decimal = Decimal('0')
    total_credit_balance: Decimal = Decimal('0')
    units: List[UnitData] = []

    class Config:
        json_encoders = {Decimal: str}
