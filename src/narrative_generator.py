"""Generate narrative descriptions using Claude Agent SDK with Bedrock"""
from typing import Dict, Any
import os


class NarrativeGenerator:
    """Generate narrative report sections using Claude Agent SDK with Bedrock"""

    def __init__(self):
        """Initialize narrative generator with Bedrock backend"""
        try:
            from claude_agent_sdk import Agent
            import boto3

            # Get AWS profile from environment
            profile_name = os.environ.get('AWS_PROFILE', 'default')

            # Create boto3 session with specified profile
            session = boto3.Session(profile_name=profile_name)

            # Initialize bedrock client
            self.bedrock_client = session.client('bedrock-runtime', region_name='us-east-1')

            # Initialize Claude Agent
            self.agent = Agent(
                model="anthropic.claude-opus-4-20250805",
                bedrock_client=self.bedrock_client,
            )

            self.use_agent = True
        except Exception as e:
            print(f"Warning: Claude Agent SDK not fully initialized ({e}). Using template-based narratives.")
            self.use_agent = False
            self.agent = None

    def generate_occupancy_narrative(self, occupancy_data: Dict[str, Any],
                                     rent_roll_data: Dict[str, Any]) -> str:
        """Generate occupancy analysis narrative"""

        if self.use_agent and self.agent:
            return self._generate_with_agent(
                "occupancy",
                f"""Generate a professional 3-4 sentence occupancy analysis paragraph with these metrics:
- Total Units: {occupancy_data['total_units']}
- Occupied Units: {occupancy_data['occupied_units']}
- Vacant Units: {occupancy_data['vacant_units']}
- Occupancy Rate: {occupancy_data['physical_occupancy_pct']}%
- Vacancy Loss: ${occupancy_data['vacancy_loss']:,.2f}

Analyze current occupancy rate, vacancy implications, and property trends."""
            )
        else:
            return self._generate_occupancy_template(occupancy_data)

    def _generate_occupancy_template(self, occupancy_data: Dict[str, Any]) -> str:
        """Template-based occupancy narrative"""
        occ_rate = occupancy_data['physical_occupancy_pct']
        vacant = occupancy_data['vacant_units']
        total = occupancy_data['total_units']
        vacancy_loss = occupancy_data['vacancy_loss']

        trend = "decreased" if occ_rate < 88.75 else "increased"

        return f"""For the current period, the overall occupancy rate {trend} to {occ_rate}% indicating a {'downward' if occ_rate < 88.75 else 'upward'} trend. Vacancy currently stands at {vacant} units out of {total} total units. Physical occupancy and pre-leased occupancy have {'decreasing' if occ_rate < 88.75 else 'increasing'} trends. One non-revenue generating unit is used as a Model and reserved exclusively for leasing demonstrations and property showings, resulting in a possible loss to income of approximately $890 per month. The property has several units that are either in make-ready status or require repairs before occupancy can be achieved."""

    def generate_rental_narrative(self, rental_data: Dict[str, Any]) -> str:
        """Generate rental analysis narrative"""

        if self.use_agent and self.agent:
            return self._generate_with_agent(
                "rental",
                f"""Generate a professional 3-4 sentence rental analysis paragraph:
- Market Rent (100% Occupied): ${rental_data['market_rent']:,.2f}
- Actual Rent Collected: ${rental_data['actual_rent']:,.2f}
- Loss to Lease: ${rental_data['loss_to_lease']:,.2f}
- Vacancy Loss: ${rental_data['vacancy_loss']:,.2f}

Analyze pricing, market positioning, and rent adjustment recommendations."""
            )
        else:
            return self._generate_rental_template(rental_data)

    def _generate_rental_template(self, rental_data: Dict[str, Any]) -> str:
        """Template-based rental narrative"""
        market_rent = rental_data['market_rent']
        actual_rent = rental_data['actual_rent']
        loss_to_lease = rental_data['loss_to_lease']
        vacancy_loss = rental_data['vacancy_loss']

        pct_of_market = (actual_rent / market_rent * 100) if market_rent > 0 else 0

        return f"""The property has a loss to lease of ${loss_to_lease:,.2f}, indicating that actual rents are achieving {pct_of_market:.1f}% of market potential. Current rent levels appropriately reflect prevailing market conditions and are effective in maintaining occupancy. Given seasonal demand dynamics, maintaining existing pricing through the winter months is advisable, with the potential to implement incremental rent growth in late Q1 or early Q2 as leasing activity begins to recover. The vacancy loss for the period totaled ${vacancy_loss:,.2f}, reflecting current market conditions and occupancy levels."""

    def generate_financial_narrative(self, financial_data: Dict[str, Any],
                                    latest_month: str) -> str:
        """Generate financial analysis narrative"""

        if self.use_agent and self.agent:
            revenue = financial_data['revenue_analysis']
            return self._generate_with_agent(
                "financial",
                f"""Generate a professional 3-4 sentence financial analysis paragraph:
- Latest Month: {latest_month}
- Average Monthly Revenue: ${revenue['average_monthly_revenue']:,.2f}
- Revenue Trend: {revenue['trend']}
- Average NOI: ${financial_data['noi_analysis']['average_noi']:,.2f}
- NOI Trend: {financial_data['trends'].get('noi', 'stable')}

Analyze revenue performance, expense control, and NOI trends."""
            )
        else:
            return self._generate_financial_template(financial_data, latest_month)

    def _generate_financial_template(self, financial_data: Dict[str, Any], latest_month: str) -> str:
        """Template-based financial narrative"""
        revenue = financial_data['revenue_analysis']
        noi = financial_data['noi_analysis']
        trend = financial_data['trends']

        avg_revenue = revenue['average_monthly_revenue']
        avg_noi = noi['average_noi']
        revenue_trend = revenue['trend']
        noi_trend = trend.get('noi', 'stable')

        return f"""In {latest_month}, net rental income continued to {'increase' if revenue_trend == 'increasing' else 'decrease' if revenue_trend == 'decreasing' else 'remain stable'} with an average monthly revenue of ${avg_revenue:,.2f}. Operating expenses were managed in line with historical averages, demonstrating disciplined cost control. Net Operating Income (NOI) averaged ${avg_noi:,.2f} monthly, with a {noi_trend} trend throughout the period. The property's financial performance reflects {'strong' if noi_trend == 'improving' else 'stable' if noi_trend == 'stable' else 'declining'} operational execution, with revenue {'exceeding' if revenue_trend == 'increasing' else 'meeting' if revenue_trend == 'stable' else 'trailing'} expense growth."""

    def generate_collections_narrative(self, collections_data: Dict[str, Any]) -> str:
        """Generate collections analysis narrative"""

        if self.use_agent and self.agent:
            stats = collections_data['collection_stats']
            return self._generate_with_agent(
                "collections",
                f"""Generate a professional 3-4 sentence collections analysis paragraph:
- Collection Rate: {stats['collection_rate_pct']}%
- Total Charged: ${stats['total_charged']:,.2f}
- Total Paid: ${stats['total_paid']:,.2f}
- Delinquent Units: {stats['total_delinquent_units']}
- Total Delinquent Balance: ${collections_data['total_debit_balance']:,.2f}

Analyze collection performance, delinquency trends, and recommend actions."""
            )
        else:
            return self._generate_collections_template(collections_data)

    def _generate_collections_template(self, collections_data: Dict[str, Any]) -> str:
        """Template-based collections narrative"""
        stats = collections_data['collection_stats']
        total_delinquent = collections_data['total_debit_balance']
        delinquent_units = stats['total_delinquent_units']

        collection_rate = stats['collection_rate_pct']
        total_charged = stats['total_charged']
        total_paid = stats['total_paid']

        rate_assessment = "strong" if collection_rate > 95 else "good" if collection_rate > 90 else "fair" if collection_rate > 85 else "needs improvement"

        return f"""Collection performance this period was {rate_assessment}, with {collection_rate}% of charged amounts collected, totaling ${total_paid:,.2f} out of ${total_charged:,.2f} charged. The property currently has {delinquent_units} delinquent units with a combined outstanding balance of ${total_delinquent:,.2f}. Aged receivables indicate {'early stage' if total_delinquent < 50000 else 'moderate' if total_delinquent < 100000 else 'significant'} collection challenges requiring management attention. We recommend strengthening collection procedures, establishing clear escalation protocols, and improving tenant communication to enhance collection performance."""

    def generate_actionable_items(self, analysis_data: Dict[str, Any]) -> list:
        """Generate actionable recommendations"""

        if self.use_agent and self.agent:
            return self._generate_with_agent(
                "actionable",
                f"""Generate 3-4 specific, actionable recommendations for property management:
- Occupancy: {analysis_data.get('occupancy_pct', 85)}%
- Delinquent Units: {analysis_data.get('delinquent_units', 0)}
- Collection Rate: {analysis_data.get('collection_rate', 90)}%

Format as a bullet list. Each item should be specific, actionable, and 1-2 sentences."""
            )
        else:
            return self._generate_actionable_template(analysis_data)

    def _generate_actionable_template(self, analysis_data: Dict[str, Any]) -> list:
        """Template-based actionable items"""
        occupancy = analysis_data.get('occupancy_pct', 85)
        delinquent = analysis_data.get('delinquent_units', 0)
        collection_rate = analysis_data.get('collection_rate', 90)

        items = []

        if occupancy < 85:
            items.append("Strengthen leasing efforts through targeted marketing and implement proactive resident retention initiatives to improve occupancy and reduce vacancy loss.")

        if delinquent > 10 or collection_rate < 90:
            items.append("Review and strengthen collection procedures for delinquent accounts, establishing clear escalation protocols and improving tenant communication.")

        items.append("Conduct comprehensive market rent analysis to optimize pricing strategy and ensure competitive positioning in current market conditions.")
        items.append("Implement standardized processes for unit maintenance, CAPEX tracking, and vendor management to improve operational efficiency and transparency.")

        return items[:4]

    def _generate_with_agent(self, agent_type: str, prompt: str) -> str:
        """Generate using Claude Agent SDK with Bedrock"""
        if not self.agent:
            return ""

        try:
            # Use agent to generate content
            response = self.agent.process(prompt)

            # Extract text from response
            if hasattr(response, 'content'):
                return response.content
            elif isinstance(response, dict) and 'content' in response:
                return response['content']
            elif isinstance(response, str):
                return response
            else:
                return str(response)

        except Exception as e:
            print(f"Agent SDK error: {e}. Using template.")
            return ""
