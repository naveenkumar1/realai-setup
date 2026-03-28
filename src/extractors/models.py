"""Data models for rent roll and T12 financial data."""
from decimal import Decimal
from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class UnitRecord:
    unit: str
    tenant: str
    sq_ft: int
    deposit: Decimal
    market_rent: Decimal
    vacancy_loss: Decimal
    loss_to_lease: Decimal
    rent_charges: Decimal
    misc_charges: Decimal
    credits: Decimal
    prior_balance: Decimal
    total_charged: Decimal
    total_paid: Decimal
    credit_balance: Decimal
    debit_balance: Decimal

    @property
    def status(self) -> str:
        return "vacant" if self.tenant.upper().startswith("VACANT") else "occupied"

    @property
    def is_model(self) -> bool:
        return "MODEL" in self.unit.upper() or "MODEL" in self.tenant.upper()


@dataclass
class RentRollSummary:
    property_name: str
    period_start: str
    period_end: str
    report_date: str
    total_units: int
    vacant_units: int
    occupied_units: int
    total_sq_ft: int
    deposits_held: Decimal
    market_rent: Decimal
    vacancy_loss: Decimal
    loss_to_lease: Decimal
    rent_charges: Decimal
    misc_charges: Decimal
    credits: Decimal
    prior_balance: Decimal
    total_charged: Decimal
    total_paid: Decimal
    credit_balances: Decimal
    debit_balances: Decimal
    credit_balance_count: int
    overall_balance: Decimal
    units: List[UnitRecord] = field(default_factory=list)


@dataclass
class T12MonthData:
    """All financial data for one month from the T12."""
    month: str
    gross_potential_rent: Decimal = Decimal('0')
    loss_to_old_lease: Decimal = Decimal('0')
    vacancy_loss: Decimal = Decimal('0')
    loss_to_employee: Decimal = Decimal('0')
    concessions: Decimal = Decimal('0')
    write_off_uncollectable: Decimal = Decimal('0')
    total_rental_income: Decimal = Decimal('0')
    application_fees: Decimal = Decimal('0')
    appliance_rental: Decimal = Decimal('0')
    internet_income: Decimal = Decimal('0')
    late_charges: Decimal = Decimal('0')
    parking_income: Decimal = Decimal('0')
    pet_charges: Decimal = Decimal('0')
    pest_control_fees: Decimal = Decimal('0')
    renters_insurance: Decimal = Decimal('0')
    admin_fees: Decimal = Decimal('0')
    mtm_fees: Decimal = Decimal('0')
    utility_water: Decimal = Decimal('0')
    utility_trash: Decimal = Decimal('0')
    total_other_income: Decimal = Decimal('0')
    total_income: Decimal = Decimal('0')
    total_administrative: Decimal = Decimal('0')
    total_marketing: Decimal = Decimal('0')
    total_payroll: Decimal = Decimal('0')
    total_repairs: Decimal = Decimal('0')
    total_unit_preparation: Decimal = Decimal('0')
    total_contract_services: Decimal = Decimal('0')
    total_utilities: Decimal = Decimal('0')
    total_insurance_taxes: Decimal = Decimal('0')
    total_expenses: Decimal = Decimal('0')
    noi: Decimal = Decimal('0')
    total_debt_service: Decimal = Decimal('0')
    total_partnership: Decimal = Decimal('0')
    total_capital: Decimal = Decimal('0')
    total_non_recurring_capital: Decimal = Decimal('0')
    net_income: Decimal = Decimal('0')
    managers_salary: Decimal = Decimal('0')
    leasing_agents: Decimal = Decimal('0')
    maintenance_supervisor: Decimal = Decimal('0')
    assistant_maintenance: Decimal = Decimal('0')
    bonuses: Decimal = Decimal('0')
    payroll_insurance: Decimal = Decimal('0')
    payroll_taxes: Decimal = Decimal('0')


@dataclass
class T12Data:
    property_name: str
    months: Dict[str, T12MonthData] = field(default_factory=dict)
