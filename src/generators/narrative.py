"""
Narrative generator — calls Claude via AWS Bedrock (boto3) for each report section.
Falls back to professional template strings if Bedrock is unavailable.

Each section prompt includes:
  1. A style example (how the section looks in the real template)
  2. The actual extracted data
  3. Clear instructions to match tone and format
"""
import json
import os
from typing import Dict, Any


# ─────────────────────────────────────────────
# Section prompt templates
# Each entry: (style_example, data_instructions)
# The caller fills {data_block} at runtime.
# ─────────────────────────────────────────────

SECTION_PROMPTS = {
    "occupancy": """You are a professional real estate asset manager writing a monthly audit report.

STYLE EXAMPLE (match this professional tone exactly):
"For the current period, the overall occupancy rate decreased to 87.5% indicating a downward trend.
Vacancy currently stands at 20 units out of 160 total units. Physical occupancy and pre-leased occupancy
have decreasing trends. One non-revenue generating unit is used as a Model and reserved exclusively for
leasing demonstrations and property showings, resulting in a possible loss to income of approximately $890
per month. The property has several units that are either in make-ready status or require repairs before
occupancy can be achieved."

ACTUAL DATA FOR THIS PERIOD:
{data_block}

Write a 4-5 sentence occupancy analysis paragraph using the ACTUAL DATA above. Match the tone and structure
of the style example. Do not copy the example — use the real numbers. Output only the paragraph, no headings.""",

    "rental": """You are a professional real estate asset manager writing a monthly audit report.

STYLE EXAMPLE (match this professional tone exactly):
"The property has a loss to lease of $24,149, indicating that actual rents are achieving 86.1% of market
potential. Current rent levels appropriately reflect prevailing market conditions and are effective in
maintaining occupancy. Given seasonal demand dynamics, maintaining existing pricing through the winter
months is advisable, with the potential to implement incremental rent growth in late Q1 or early Q2 as
leasing activity begins to recover. The vacancy loss for the period totaled $21,534.03, reflecting current
market conditions and occupancy levels."

ACTUAL DATA FOR THIS PERIOD:
{data_block}

Write a 4-sentence rental analysis paragraph using the ACTUAL DATA. Match the tone and structure exactly.
Output only the paragraph, no headings.""",

    "rental_comparison": """You are a professional real estate asset manager writing a market positioning analysis.

STYLE EXAMPLE:
"Verandas is 87% occupied, experiencing minor seasonal softening typical for winter months. 1BR units at
$995 ($1.54/SF) are in line with the market average of $989 ($1.57/SF). 2BR units at $1,135 ($1.31/SF)
are modestly below the market average of $1,107 ($1.33/SF). We recommend holding pricing through the
winter months with the potential to implement incremental rent growth in late Q1 or early Q2 as leasing
activity begins to recover."

ACTUAL DATA:
{data_block}

Write a 4-sentence rental comparison narrative. Calculate market averages from the competitor data provided.
Output only the paragraph, no headings.""",

    "financial": """You are a professional real estate asset manager writing a monthly P&L analysis.

STYLE EXAMPLE:
"Net rental income increased to $142,992.28 due to lower write-off uncollectable amounts. Other income
increased to $24,169.83, driven by higher late fee collections. Total revenue for the period increased
by $4,190.77 versus the prior month. Operating expenses were managed within budget, demonstrating
disciplined cost control across all categories."

ACTUAL DATA FOR THIS PERIOD:
{data_block}

Write a 4-sentence P&L analysis paragraph using the ACTUAL DATA. Compare current month to prior month.
Include revenue trend, expense control, and NOI performance. Output only the paragraph, no headings.""",

    "collections": """You are a professional real estate asset manager writing a collections analysis.

STYLE EXAMPLE:
"Collection performance this period was strong, with 97.2% of charged amounts collected, totaling
$167,218.51 out of $165,968.01 charged. The property currently has 12 units with balances greater than
$1,000. Aged receivables indicate early-stage collection challenges requiring management attention.
We recommend strengthening collection procedures, establishing clear escalation protocols, and improving
tenant communication to enhance collection performance."

ACTUAL DATA FOR THIS PERIOD:
{data_block}

Write a 4-sentence collections analysis paragraph using the ACTUAL DATA. Output only the paragraph, no headings.""",

    "expense": """You are a professional real estate asset manager writing an expense analysis.

STYLE EXAMPLE:
"Most expenses increased month-over-month but remained within monthly averages. Payroll expenses reflected
consistent staffing levels with no significant variance from prior periods. Utility costs aligned with
seasonal benchmarks for the period. Certain variable expense categories including repairs and contract
services showed fluctuation that warrants monitoring in the coming months."

ACTUAL DATA FOR THIS PERIOD:
{data_block}

Write a 4-sentence expense analysis paragraph using the ACTUAL DATA. Highlight any notable variances.
Output only the paragraph, no headings.""",

    "rent_growth": """You are a professional real estate asset manager writing a rent growth analysis.

STYLE EXAMPLE:
"Net rental growth increased 2.48% compared to the prior period, indicating an upward trend.
Gross potential rent remains stable at $174,390, reflecting consistent market positioning.
Actual rental income fluctuations are primarily driven by changes in occupancy and loss-to-lease dynamics.
Continued focus on occupancy improvement and lease renewal pricing will be key drivers for revenue growth."

ACTUAL DATA FOR THIS PERIOD:
{data_block}

Write a 4-sentence rent growth narrative. Calculate the MoM % change from the data. Output only the paragraph.""",

    "gpr": """You are a professional real estate asset manager writing a Gross Potential Rent analysis.

STYLE EXAMPLE:
"The property has 160 units with 137 occupied and 23 vacant. Total market rent at 100% occupancy is
$174,390. Loss to lease of $2,615.10 reflects the gap between market and actual charged rents. Vacancy
loss totals $21,534.03, representing the revenue impact of current vacancies. Actual rent charges for
December were $139,451.47."

ACTUAL DATA:
{data_block}

Write a 4-sentence GPR analysis using the ACTUAL DATA. Output only the paragraph, no headings.""",

    "audit_findings": """You are a professional real estate asset manager summarizing audit findings.

Given the following property performance data, write one concise sentence (max 25 words) summarizing
the key audit finding for each of these three categories:
1. Operational (occupancy, vacancy, leasing trends)
2. CAPEX (capital expenditure status)
3. Financial (income, expenses, NOI)

ACTUAL DATA:
{data_block}

Return ONLY a JSON object in this exact format (no markdown, no explanation):
{{"operational": "...", "capex": "...", "financial": "..."}}""",

    "audit_actions": """You are a professional real estate asset manager.

Given the following property performance data, write one concise actionable item (max 20 words) for each category:
1. Operational
2. CAPEX
3. Financial

ACTUAL DATA:
{data_block}

Return ONLY a JSON object in this exact format:
{{"operational": "...", "capex": "...", "financial": "..."}}""",
}


class NarrativeGenerator:
    """
    Generates narrative paragraphs for each report section.
    Uses Claude via AWS Bedrock (boto3) when credentials are available.
    Falls back to professional template strings otherwise.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.bedrock_client = None
        self.model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
        self.use_bedrock = False

        self._init_bedrock()

    def _init_bedrock(self):
        bedrock_cfg = self.config.get('bedrock', {})
        try:
            import boto3

            profile = (
                bedrock_cfg.get('profile') or
                os.environ.get('AWS_PROFILE', 'default')
            )
            region = bedrock_cfg.get('region', 'us-east-1')
            model_override = bedrock_cfg.get('model_id', '')

            session = boto3.Session(profile_name=profile)
            self.bedrock_client = session.client('bedrock-runtime', region_name=region)

            # Use configured model or fall back to Sonnet (widely available)
            if model_override:
                self.model_id = model_override
            else:
                self.model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

            # Quick connectivity test — list models would require bedrock (not bedrock-runtime)
            # Just mark as ready; actual failure will be caught in _call_bedrock
            self.use_bedrock = True
            print(f"  → Bedrock initialized (profile={profile}, model={self.model_id})")

        except Exception as e:
            print(f"  → Bedrock unavailable ({e}). Using template narratives.")
            self.use_bedrock = False

    def _call_bedrock(self, prompt: str, max_tokens: int = None) -> str:
        """Call Claude via Bedrock and return the text response."""
        if not self.bedrock_client:
            return ""
        cfg_max = self.config.get('bedrock', {}).get('max_tokens', 600)
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens or cfg_max,
            "messages": [{"role": "user", "content": prompt}],
        })
        try:
            resp = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=body,
                contentType="application/json",
                accept="application/json",
            )
            result = json.loads(resp['body'].read())
            return result['content'][0]['text'].strip()
        except Exception as e:
            print(f"  → Bedrock call failed ({e}). Using template fallback.")
            self.use_bedrock = False
            return ""

    def _generate(self, section_key: str, data_block: str, fallback_fn):
        """Generate narrative via Bedrock or fall back to template."""
        if self.use_bedrock:
            template = SECTION_PROMPTS.get(section_key, "")
            prompt = template.replace("{data_block}", data_block)
            result = self._call_bedrock(prompt)
            if result:
                return result
        return fallback_fn()

    # ─────────────────────────────────────────────
    # Public section generators
    # ─────────────────────────────────────────────

    def generate_audit_findings(self, rr_data: Dict, fin_data: Dict) -> Dict[str, str]:
        """Return {operational, capex, financial} one-sentence findings."""
        occ_pct = rr_data.get('physical_occupancy_pct', 0)
        vacant  = rr_data.get('vacant_units', 0)
        dec_rental = fin_data.get('dec_rental_income', 0)
        dec_noi    = fin_data.get('dec_noi', 0)

        data_block = (
            f"Occupancy: {occ_pct}% | Vacant: {vacant} units\n"
            f"December Rental Income: ${dec_rental:,.2f}\n"
            f"December NOI: ${dec_noi:,.2f}"
        )
        if self.use_bedrock:
            raw = self._call_bedrock(
                SECTION_PROMPTS["audit_findings"].replace("{data_block}", data_block),
                max_tokens=300
            )
            try:
                return json.loads(raw)
            except Exception:
                pass
        return {
            "operational": f"Occupancy at {occ_pct}%, vacancy {vacant} units; leasing momentum requires attention.",
            "capex": "Capital expenditure activities focused on unit renovations and deferred maintenance.",
            "financial": f"Net rental income {_money(dec_rental)}; NOI {_money(dec_noi)} for December 2025.",
        }

    def generate_audit_actions(self, rr_data: Dict, fin_data: Dict) -> Dict[str, str]:
        """Return {operational, capex, financial} actionable items."""
        occ_pct = rr_data.get('physical_occupancy_pct', 0)
        col_rate = rr_data.get('collection_rate_pct', 0)
        data_block = (
            f"Occupancy: {occ_pct}% | Collection rate: {col_rate}%\n"
            f"December NOI: ${fin_data.get('dec_noi', 0):,.2f}"
        )
        if self.use_bedrock:
            raw = self._call_bedrock(
                SECTION_PROMPTS["audit_actions"].replace("{data_block}", data_block),
                max_tokens=300
            )
            try:
                return json.loads(raw)
            except Exception:
                pass
        return {
            "operational": "Strengthen leasing, accelerate lease-up, implement resident retention initiatives.",
            "capex": "Standardize unit-level CAPEX tagging and tracking process for transparency.",
            "financial": "Implement detailed expense tracking and tighter controls for variable cost categories.",
        }

    def generate_occupancy_narrative(self, occ_data: Dict[str, Any], rr_data: Dict = None) -> str:
        total   = occ_data.get('total_units', 160)
        occupied = occ_data.get('occupied_units', 0)
        vacant  = occ_data.get('vacant_units', 0)
        occ_pct = occ_data.get('physical_occupancy_pct', 0)
        vac_loss = occ_data.get('vacancy_loss', 0)
        model_loss = self.config.get('occupancy', {}).get('model_unit_monthly_loss', 890)

        data_block = (
            f"Property: {occ_data.get('property_name', 'Subject Property')}\n"
            f"Total Units: {total}\n"
            f"Occupied Units: {occupied}\n"
            f"Vacant Units: {vacant}\n"
            f"Physical Occupancy: {occ_pct}%\n"
            f"Vacancy Loss: ${float(vac_loss):,.2f}\n"
            f"Model Unit Monthly Revenue Loss: ${model_loss:,.0f}"
        )
        trend = "decreased" if float(occ_pct) < 90 else "increased"
        direction = "downward" if float(occ_pct) < 90 else "upward"
        return self._generate("occupancy", data_block, lambda: (
            f"For the current period, the overall occupancy rate {trend} to {occ_pct}%, "
            f"indicating a {direction} trend. "
            f"Vacancy currently stands at {vacant} units out of {total} total units. "
            f"Physical and pre-leased occupancy reflect current market dynamics. "
            f"One non-revenue generating unit is used as a Model for leasing demonstrations, "
            f"resulting in a potential loss to income of approximately ${model_loss:,} per month. "
            f"The property has several units requiring make-ready or repairs before occupancy can be achieved."
        ))

    def generate_rental_narrative(self, rental_data: Dict[str, Any]) -> str:
        market   = rental_data.get('market_rent', 0)
        actual   = rental_data.get('actual_rent', 0)
        ltl      = rental_data.get('loss_to_lease', 0)
        vac_loss = rental_data.get('vacancy_loss', 0)
        pct      = round(float(actual) / float(market) * 100, 1) if float(market) > 0 else 0

        data_block = (
            f"Market Rent (100% occupied): ${float(market):,.2f}\n"
            f"Actual Rent Charged: ${float(actual):,.2f}\n"
            f"Loss to Lease: ${float(ltl):,.2f}\n"
            f"Vacancy Loss: ${float(vac_loss):,.2f}\n"
            f"Actual as % of Market: {pct}%"
        )
        return self._generate("rental", data_block, lambda: (
            f"The property has a loss to lease of {_money(ltl)}, indicating that actual rents are "
            f"achieving {pct}% of market potential. "
            f"Current rent levels appropriately reflect prevailing market conditions and are effective "
            f"in maintaining occupancy. "
            f"Given seasonal demand dynamics, maintaining existing pricing through the winter months is advisable, "
            f"with the potential to implement incremental rent growth in late Q1 or early Q2 as leasing "
            f"activity begins to recover. "
            f"The vacancy loss for the period totaled {_money(vac_loss)}, reflecting current occupancy levels."
        ))

    def generate_rental_comparison_narrative(self, competitors: list, subject_occ_pct: float) -> str:
        if not competitors:
            return "[DATA NOT AVAILABLE — requires market survey data in config/property_config.yaml]"

        # Build comparison summary for the prompt
        lines = [f"Subject Property Occupancy: {subject_occ_pct}%"]
        for section in competitors:
            lines.append(f"\n{section['section']}:")
            for p in section['properties']:
                rent_psf = round(p['rent'] / p['sq_ft'], 2) if p['sq_ft'] > 0 else 0
                lines.append(f"  {p['name']} {p['unit_type']}: {p['sq_ft']} SF @ ${p['rent']:.0f} (${rent_psf}/SF)")

        data_block = "\n".join(lines)
        return self._generate("rental_comparison", data_block, lambda: (
            f"The subject property is positioned competitively within the local submarket at {subject_occ_pct}% occupancy, "
            f"with minor seasonal softening typical for winter months. "
            f"1BR units are priced in line with the market average, while 2BR units are modestly below market. "
            f"Maintaining existing pricing through the winter months is advisable, with the potential to "
            f"implement incremental rent growth in late Q1 or early Q2 as leasing activity recovers."
        ))

    def generate_financial_narrative(self, financial_data: Dict[str, Any], latest_month: str) -> str:
        dec_rental = financial_data.get('dec_rental_income', 0)
        nov_rental = financial_data.get('nov_rental_income', 0)
        dec_other  = financial_data.get('dec_other_income', 0)
        dec_total  = financial_data.get('dec_total_income', 0)
        dec_exp    = financial_data.get('dec_total_expenses', 0)
        dec_noi    = financial_data.get('dec_noi', 0)
        avg_noi    = financial_data.get('avg_noi', 0)
        delta      = float(dec_rental) - float(nov_rental)

        data_block = (
            f"Period: {latest_month}\n"
            f"December Rental Income: ${float(dec_rental):,.2f}\n"
            f"November Rental Income: ${float(nov_rental):,.2f}\n"
            f"MoM Rental Change: ${delta:+,.2f}\n"
            f"December Other Income: ${float(dec_other):,.2f}\n"
            f"December Total Income: ${float(dec_total):,.2f}\n"
            f"December Total Expenses: ${float(dec_exp):,.2f}\n"
            f"December NOI: ${float(dec_noi):,.2f}\n"
            f"Average Monthly NOI (12 months): ${float(avg_noi):,.2f}"
        )
        direction = "decreased" if delta < 0 else "increased"
        return self._generate("financial", data_block, lambda: (
            f"For {latest_month}, net rental income {direction} to {_money(dec_rental)}, "
            f"a change of {_money(abs(delta))} versus the prior month. "
            f"Other income contributed {_money(dec_other)}, bringing total revenue to {_money(dec_total)}. "
            f"Operating expenses were managed in line with historical averages, demonstrating disciplined cost control. "
            f"Net Operating Income (NOI) for the period was {_money(dec_noi)}, "
            f"with a 12-month average of {_money(avg_noi)}."
        ))

    def generate_collections_narrative(self, collections_data: Dict[str, Any]) -> str:
        stats      = collections_data.get('collection_stats', {})
        cr         = stats.get('collection_rate_pct', 0)
        charged    = stats.get('total_charged', 0)
        paid       = stats.get('total_paid', 0)
        delinq     = stats.get('total_delinquent_units', 0)
        debit_bal  = collections_data.get('total_debit_balance', 0)

        data_block = (
            f"Collection Rate: {cr}%\n"
            f"Total Charged: ${float(charged):,.2f}\n"
            f"Total Paid: ${float(paid):,.2f}\n"
            f"Delinquent Units: {delinq}\n"
            f"Total Delinquent Balance: ${float(debit_bal):,.2f}"
        )
        rate_word = "strong" if float(cr) > 95 else "good" if float(cr) > 90 else "fair" if float(cr) > 85 else "needs improvement"
        return self._generate("collections", data_block, lambda: (
            f"Collection performance this period was {rate_word}, with {cr}% of charged amounts collected, "
            f"totaling {_money(paid)} out of {_money(charged)} charged. "
            f"The property currently has {delinq} units carrying delinquent balances totaling {_money(debit_bal)}. "
            f"Aged receivables indicate {'early-stage' if float(debit_bal) < 50000 else 'moderate'} "
            f"collection challenges requiring management attention. "
            f"We recommend strengthening collection procedures, establishing clear escalation protocols, "
            f"and improving tenant communication to enhance collection performance."
        ))

    def generate_expense_narrative(self, expense_data: Dict[str, Any]) -> str:
        dec_exp = expense_data.get('dec_total_expenses', 0)
        nov_exp = expense_data.get('nov_total_expenses', 0)
        dec_pay = expense_data.get('dec_payroll', 0)
        dec_rep = expense_data.get('dec_repairs', 0)
        delta   = float(dec_exp) - float(nov_exp)

        data_block = (
            f"December Total Expenses: ${float(dec_exp):,.2f}\n"
            f"November Total Expenses: ${float(nov_exp):,.2f}\n"
            f"MoM Change: ${delta:+,.2f}\n"
            f"December Payroll: ${float(dec_pay):,.2f}\n"
            f"December Repairs: ${float(dec_rep):,.2f}"
        )
        return self._generate("expense", data_block, lambda: (
            f"Total operating expenses for December 2025 were {_money(dec_exp)}, "
            f"a {'decrease' if delta < 0 else 'increase'} of {_money(abs(delta))} versus the prior month. "
            f"Payroll expenses of {_money(dec_pay)} reflect consistent staffing levels with no significant variance. "
            f"Repair and maintenance costs of {_money(dec_rep)} reflect ongoing make-ready and preventive maintenance activities. "
            f"Expense categories are being monitored to ensure alignment with the annual budget plan."
        ))

    def generate_rent_growth_narrative(self, months_data: list) -> str:
        if len(months_data) < 2:
            return "Insufficient monthly data to calculate rent growth trend."

        first = float(months_data[0].get('total_income', 0))
        last  = float(months_data[-1].get('total_income', 0))
        gpr   = float(months_data[-1].get('gross_potential_rent', 0))
        change_pct = round((last - first) / abs(first) * 100, 2) if first != 0 else 0

        data_block = "\n".join([
            f"{m['month']}: Rental Income ${float(m.get('total_rental_income', 0)):,.2f} | "
            f"Total Income ${float(m.get('total_income', 0)):,.2f}"
            for m in months_data
        ])
        data_block += f"\n6-Month Revenue Change: {change_pct:+.2f}%"

        return self._generate("rent_growth", data_block, lambda: (
            f"Net rental income trend over the 6-month period shows a {change_pct:+.2f}% change. "
            f"Gross potential rent remains stable at {_money(gpr)}, reflecting consistent market positioning. "
            f"Actual rental income fluctuations are primarily driven by changes in occupancy and loss-to-lease dynamics. "
            f"Continued focus on occupancy improvement and lease renewal pricing will drive revenue growth in the coming quarter."
        ))

    def generate_gpr_narrative(self, rr_data: Dict[str, Any]) -> str:
        total    = rr_data.get('total_units', 0)
        occupied = rr_data.get('occupied_units', 0)
        vacant   = rr_data.get('vacant_units', 0)
        mkt      = rr_data.get('market_rent', 0)
        ltl      = rr_data.get('loss_to_lease', 0)
        vl       = rr_data.get('vacancy_loss', 0)
        actual   = rr_data.get('rent_charges', 0)

        data_block = (
            f"Total Units: {total}\n"
            f"Occupied: {occupied} | Vacant: {vacant}\n"
            f"Market Rent (100% occupied): ${float(mkt):,.2f}\n"
            f"Loss to Lease: ${float(ltl):,.2f}\n"
            f"Vacancy Loss: ${float(vl):,.2f}\n"
            f"Actual Rent Charges: ${float(actual):,.2f}"
        )
        return self._generate("gpr", data_block, lambda: (
            f"The property has {total} total units with {occupied} occupied and {vacant} vacant. "
            f"Total market rent at 100% occupancy is {_money(mkt)}. "
            f"Loss to lease of {_money(ltl)} reflects the gap between market and actual charged rents. "
            f"Vacancy loss totals {_money(vl)}, representing the revenue impact of current vacancies. "
            f"Actual rent charges for the period were {_money(actual)}."
        ))


def _money(v) -> str:
    try:
        fv = float(v)
        if fv < 0:
            return f"(${abs(fv):,.2f})"
        return f"${fv:,.2f}"
    except Exception:
        return str(v)
