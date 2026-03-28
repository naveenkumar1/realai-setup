"""T12 Profit & Loss PDF extractor."""
import re
from decimal import Decimal
from .models import T12MonthData, T12Data


def _d(s: str) -> Decimal:
    s = s.replace(',', '').replace('$', '').strip()
    if not s or s == '-':
        return Decimal('0')
    try:
        return Decimal(s)
    except Exception:
        return Decimal('0')


class T12Extractor:
    """
    Parse the T12 Profit & Loss PDF.
    Column order: JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC TOTAL
    """

    MONTH_KEYS = [
        'JAN 25', 'FEB 25', 'MAR 25', 'APR 25', 'MAY 25', 'JUN 25',
        'JUL 25', 'AUG 25', 'SEP 25', 'OCT 25', 'NOV 25', 'DEC 25',
    ]

    # (regex_pattern, attribute_name, sign)
    LINE_MAP = [
        (r'4010\s+Gross Potential R',      'gross_potential_rent',        1),
        (r'4020\s+Loss to Old Leas',       'loss_to_old_lease',           1),
        (r'4100\s+Vacancy Loss',           'vacancy_loss',                1),
        (r'4130\s+Loss to Employe',        'loss_to_employee',            1),
        (r'4200\s+Concessions',            'concessions',                 1),
        (r'4290\s+Write Off Uncolle',      'write_off_uncollectable',     1),
        (r'4000\s+Total Rental Inco',      'total_rental_income',         1),
        (r'4410\s+Application Fees',       'application_fees',            1),
        (r'4420\s+Appliance Rental',       'appliance_rental',            1),
        (r'4426\s+Internet',               'internet_income',             1),
        (r'4480\s+New Late Charge',        'late_charges',                1),
        (r'4530\s+Month to Month',         'mtm_fees',                    1),
        (r'4550\s+Parking Income',         'parking_income',              1),
        (r'4560\s+Pet Charges',            'pet_charges',                 1),
        (r'4565\s+Pest Control Fee',       'pest_control_fees',           1),
        (r'4572\s+Renters Insuranc',       'renters_insurance',           1),
        (r'4585\s+Admin Fees',             'admin_fees',                  1),
        (r'4592\s+Utilities - Water',      'utility_water',               1),
        (r'4593\s+Utilities - Trash',      'utility_trash',               1),
        (r'4400\s+Total Other Inco',       'total_other_income',          1),
        (r'^TOTAL INCOME\b',               'total_income',                1),
        (r'5000\s+Total Administrati',     'total_administrative',        1),
        (r'5100\s+Total Marketing',        'total_marketing',             1),
        (r'5300\s+Total Payroll Exp',      'total_payroll',               1),
        (r'5500\s+Total Repairs',          'total_repairs',               1),
        (r'5600\s+Total Unit Prepar',      'total_unit_preparation',      1),
        (r'5700\s+Total Contract Se',      'total_contract_services',     1),
        (r'5800\s+Total Utilities',        'total_utilities',             1),
        (r'5900\s+Total Insurance',        'total_insurance_taxes',       1),
        (r'^TOTAL EXPENSE\b',              'total_expenses',              1),
        (r'^NOI\b',                        'noi',                         1),
        (r'6100\s+Total Debt Servic',      'total_debt_service',          1),
        (r'7000\s+Total Partnership',      'total_partnership',           1),
        (r'8000\s+Total Capital Exp',      'total_capital',               1),
        (r'8100\s+Total Non Recurri',      'total_non_recurring_capital', 1),
        (r'^NET INCOME\b',                 'net_income',                  1),
        (r'5310\s+Managers Salary',        'managers_salary',             1),
        (r'5320\s+Leasing Agents',         'leasing_agents',              1),
        (r'5330\s+Maintenance Sup',        'maintenance_supervisor',      1),
        (r'5335\s+Assistant Mainte',       'assistant_maintenance',       1),
        (r'5365\s+Bonuses',                'bonuses',                     1),
        (r'5380\s+Insurance and Ot',       'payroll_insurance',           1),
        (r'5385\s+Payroll Taxes',          'payroll_taxes',               1),
    ]

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path

    def extract(self) -> T12Data:
        import pdfplumber

        with pdfplumber.open(self.pdf_path) as pdf:
            lines = []
            property_name = "Verandas at Bear Creek"
            for page in pdf.pages:
                text = page.extract_text() or ""
                for line in text.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    if 'Property:' in line:
                        property_name = line.split('Property:')[-1].strip()
                    lines.append(line)

        data = T12Data(property_name=property_name)
        for key in self.MONTH_KEYS:
            data.months[key] = T12MonthData(month=key)

        num_pat = re.compile(r'-?\d{1,3}(?:,\d{3})*(?:\.\d+)?')

        for line in lines:
            for pattern, attr, sign in self.LINE_MAP:
                if re.search(pattern, line, re.IGNORECASE):
                    nums = num_pat.findall(line)
                    nums = [n for n in nums if '.' in n or (len(n.replace(',', '')) > 6)]
                    if len(nums) >= 12:
                        for i, key in enumerate(self.MONTH_KEYS):
                            setattr(data.months[key], attr, _d(nums[i]) * sign)
                    elif len(nums) == 1:
                        setattr(data.months['DEC 25'], attr, _d(nums[0]) * sign)
                    break

        for key in self.MONTH_KEYS:
            m = data.months[key]
            if m.total_income == 0:
                m.total_income = m.total_rental_income + m.total_other_income
            if m.total_expenses == 0:
                m.total_expenses = (
                    m.total_administrative + m.total_marketing + m.total_payroll +
                    m.total_repairs + m.total_unit_preparation + m.total_contract_services +
                    m.total_utilities + m.total_insurance_taxes
                )
            if m.noi == 0 and m.total_income != 0:
                m.noi = m.total_income - m.total_expenses

        return data
