"""Rent Roll PDF extractor — all values derived from PDF, nothing hardcoded."""
import re
from decimal import Decimal
from datetime import date
from .models import UnitRecord, RentRollSummary


def _d(s: str) -> Decimal:
    s = s.replace(',', '').replace('$', '').strip()
    if not s or s == '-':
        return Decimal('0')
    try:
        return Decimal(s)
    except Exception:
        return Decimal('0')


class RentRollExtractor:
    """Parse rent roll PDF into structured unit records and summary totals."""

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path

    def extract(self) -> RentRollSummary:
        import pdfplumber

        with pdfplumber.open(self.pdf_path) as pdf:
            all_text = ""
            for page in pdf.pages:
                all_text += (page.extract_text() or "") + "\n"

        lines = all_text.split('\n')

        # ── Header metadata ───────────────────────────────────────────────────
        property_name = ""
        period_start  = ""
        period_end    = ""
        report_date   = date.today().strftime("%m/%d/%y")

        for line in lines:
            if not property_name and 'Property:' in line:
                property_name = line.split('Property:')[-1].strip()

            if not period_start:
                m = re.search(r'Activity in the period\s+(\S+)\s*-\s*(\S+)', line)
                if m:
                    period_start, period_end = m.group(1), m.group(2)

        if not property_name:
            property_name = "Unknown Property"

        # ── Unit rows ─────────────────────────────────────────────────────────
        units   = []
        num_pat = re.compile(r'-?\d{1,3}(?:,\d{3})*\.\d{2}')

        for line in lines:
            if any(x in line for x in [
                'Tenant Name', property_name, 'Page ', 'Totals for', 'Summary Rent',
                'Deposit 100%', 'Sq Ft Held',
            ]):
                continue
            if not line.strip():
                continue

            nums = num_pat.findall(line)
            if len(nums) < 6:
                continue

            unit_match = re.search(r'\b(\d{3,4}(?:-Model)?)\b', line)
            if not unit_match:
                continue
            unit_num = unit_match.group(1)

            unit_pos = line.find(unit_match.group(0))
            tenant   = line[:unit_pos].strip()

            rest       = line[unit_pos + len(unit_match.group(0)):]
            sqft_match = re.search(r'\b(\d{3,4})\b', rest)
            sq_ft      = int(sqft_match.group(1)) if sqft_match else 0

            try:
                if len(nums) >= 12:
                    rec = UnitRecord(
                        unit=unit_num, tenant=tenant, sq_ft=sq_ft,
                        deposit=_d(nums[0]),       market_rent=_d(nums[1]),
                        vacancy_loss=_d(nums[2]),  loss_to_lease=_d(nums[3]),
                        rent_charges=_d(nums[4]),  misc_charges=_d(nums[5]),
                        credits=_d(nums[6]),        prior_balance=_d(nums[7]),
                        total_charged=_d(nums[8]), total_paid=_d(nums[9]),
                        credit_balance=_d(nums[10]), debit_balance=_d(nums[11]),
                    )
                elif len(nums) >= 6:
                    rec = UnitRecord(
                        unit=unit_num, tenant=tenant, sq_ft=sq_ft,
                        deposit=_d(nums[0]),
                        market_rent=_d(nums[1])    if len(nums) > 1 else Decimal('0'),
                        vacancy_loss=_d(nums[2])   if len(nums) > 2 else Decimal('0'),
                        loss_to_lease=Decimal('0'),
                        rent_charges=_d(nums[3])   if len(nums) > 3 else Decimal('0'),
                        misc_charges=_d(nums[4])   if len(nums) > 4 else Decimal('0'),
                        credits=Decimal('0'),       prior_balance=Decimal('0'),
                        total_charged=_d(nums[5])  if len(nums) > 5 else Decimal('0'),
                        total_paid=_d(nums[5])     if len(nums) > 5 else Decimal('0'),
                        credit_balance=Decimal('0'), debit_balance=Decimal('0'),
                    )
                else:
                    continue
                units.append(rec)
            except Exception:
                continue

        # ── Summary totals line ───────────────────────────────────────────────
        # Pattern: the numeric row immediately after "Totals for report"
        # Format: sq_ft  deposits  market_rent  vac_loss  ltl  rent_chg  misc_chg
        #         credits  prior_bal  total_chg  total_paid  credit_bal  debit_bal
        total_units          = 0
        vacant_units         = 0
        total_sq_ft          = 0
        deposits_held        = Decimal('0')
        market_rent          = Decimal('0')
        vacancy_loss         = Decimal('0')
        loss_to_lease        = Decimal('0')
        rent_charges         = Decimal('0')
        misc_charges         = Decimal('0')
        credits              = Decimal('0')
        prior_balance        = Decimal('0')
        total_charged        = Decimal('0')
        total_paid           = Decimal('0')
        credit_balances      = Decimal('0')
        debit_balances       = Decimal('0')
        credit_balance_count = 0
        overall_balance      = Decimal('0')

        int_pat = re.compile(r'\d{1,3}(?:,\d{3})+|\d+')

        for i, line in enumerate(lines):
            # ── Unit / vacancy counts + overall balance ──────────────────────
            if 'Total Units:' in line and 'Vacant Units:' in line:
                m = re.search(r'Total Units:(\d+)', line)
                if m:
                    total_units = int(m.group(1))
                m = re.search(r'Vacant Units:(\d+)', line)
                if m:
                    vacant_units = int(m.group(1))
                m = re.search(r'Credit Balances:(\d+)', line)
                if m:
                    credit_balance_count = int(m.group(1))
                m = re.search(r'Overall Balance:([\d,\.]+)', line)
                if m:
                    overall_balance = _d(m.group(1))

            # ── Financial summary row (line after "Totals for report") ────────
            if 'Totals for report' in line and i + 1 < len(lines):
                next_line = lines[i + 1]
                nums = num_pat.findall(next_line)
                int_nums = int_pat.findall(next_line)
                # First token is sq_ft (integer with commas, no decimal)
                if int_nums:
                    total_sq_ft = int(int_nums[0].replace(',', ''))
                if len(nums) >= 12:
                    deposits_held   = _d(nums[0])
                    market_rent     = _d(nums[1])
                    vacancy_loss    = _d(nums[2])
                    loss_to_lease   = _d(nums[3])
                    rent_charges    = _d(nums[4])
                    misc_charges    = _d(nums[5])
                    credits         = _d(nums[6])
                    prior_balance   = _d(nums[7])
                    total_charged   = _d(nums[8])
                    total_paid      = _d(nums[9])
                    credit_balances = _d(nums[10])
                    debit_balances  = _d(nums[11])

        return RentRollSummary(
            property_name=property_name,
            period_start=period_start,
            period_end=period_end,
            report_date=report_date,
            total_units=total_units,
            vacant_units=vacant_units,
            occupied_units=total_units - vacant_units,
            total_sq_ft=total_sq_ft,
            deposits_held=deposits_held,
            market_rent=market_rent,
            vacancy_loss=vacancy_loss,
            loss_to_lease=loss_to_lease,
            rent_charges=rent_charges,
            misc_charges=misc_charges,
            credits=credits,
            prior_balance=prior_balance,
            total_charged=total_charged,
            total_paid=total_paid,
            credit_balances=credit_balances,
            debit_balances=debit_balances,
            credit_balance_count=credit_balance_count,
            overall_balance=overall_balance,
            units=units,
        )
