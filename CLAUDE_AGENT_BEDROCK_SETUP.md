# Claude Agent SDK with Bedrock Setup Guide

This guide explains how to configure and use the Monthly Analysis Report Generator with Claude Agent SDK and AWS Bedrock for enhanced narrative generation.

## Overview

The report generator can work in two modes:

1. **Template Mode** (Default) - Uses pre-built narrative templates
2. **Claude Agent Mode** - Uses Claude Agent SDK with Bedrock for AI-generated narratives

## Prerequisites

### 1. AWS Account and Bedrock Access

- AWS Account with Bedrock service enabled
- Claude model access in Bedrock (Claude 3 or later)
- AWS credentials configured locally

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

Key packages:
- `boto3` - AWS SDK for Python
- `claude-agent-sdk` - Claude Agent SDK (when available)

## Setup Instructions

### Step 1: Configure AWS Credentials

#### Option A: Using AWS Profile (Recommended)

Set your AWS profile:

```bash
export AWS_PROFILE=your-profile-name
```

Or use the default profile:

```bash
export AWS_PROFILE=default
```

#### Option B: Using Environment Variables

```bash
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_DEFAULT_REGION=us-east-1
```

### Step 2: Enable Claude in Bedrock

1. Go to AWS Console → Bedrock
2. Navigate to "Model access"
3. Enable Claude 3 Opus or Claude 3.5 Sonnet models
4. Accept the service agreement

### Step 3: Install Claude Agent SDK

Once the SDK is available via pip:

```bash
pip install claude-agent-sdk
```

## Usage

### Basic Usage (Template Mode - No AWS Required)

```bash
python -m src.main \
  --rent-roll "data/rent_roll.pdf" \
  --financials "data/t12_financials.pdf" \
  --output "output/report.docx"
```

### Advanced Usage (Claude Agent Mode - Requires AWS Setup)

With AWS credentials configured:

```bash
export AWS_PROFILE=default
python -m src.main \
  --rent-roll "data/rent_roll.pdf" \
  --financials "data/t12_financials.pdf" \
  --output "output/report.docx"
```

The system will automatically detect AWS credentials and use Claude Agent SDK if available.

## Architecture

### Narrative Generation Flow

```
RentRollExtractor + T12Extractor
            ↓
    Analysis Engines
            ↓
NarrativeGenerator
    ├─→ Check Claude Agent SDK availability
    ├─→ If available: Use Bedrock + boto3
    └─→ If not available: Use templates
            ↓
TemplateReportGenerator
            ↓
        Word Document
```

### Supported Sections

The report automatically generates:

1. **Occupancy Analysis**
   - Physical occupancy rate
   - Vacancy trends
   - Unit status summary

2. **Rental Analysis**
   - Market vs. actual rent
   - Loss to lease
   - Pricing recommendations

3. **Financial Analysis**
   - Revenue trends
   - Expense breakdown
   - NOI analysis

4. **Collections Analysis**
   - Collection rate
   - Delinquent units
   - AR aging summary

## Configuration

### Environment Variables

- `AWS_PROFILE` - AWS profile to use (default: "default")
- `AWS_REGION` - AWS region (default: "us-east-1")
- `AWS_ACCESS_KEY_ID` - AWS access key
- `AWS_SECRET_ACCESS_KEY` - AWS secret key

### Report Template

The report matches the template structure from `data/01.26_Verandas Monthly Analysis Report.docx` with:

- Professional header and cover page
- Audit top sheet summary table
- Detailed operational analysis
- Financial performance review
- Collections summary
- Unit-level appendices
- Signature blocks

## Troubleshooting

### Issue: "Could not resolve authentication method"

**Solution:** Ensure AWS credentials are properly configured:

```bash
# Check AWS CLI is configured
aws sts get-caller-identity

# Or set environment variables
export AWS_PROFILE=your-profile
```

### Issue: "No module named 'claude_agent_sdk'"

**Solution:** Claude Agent SDK may not be publicly available yet. The system will automatically fall back to template-based narratives, which provide professional analysis without external API calls.

### Issue: "Bedrock model not found"

**Solution:** Ensure the Claude model is enabled in Bedrock:

1. Go to AWS Bedrock Console
2. Click "Model access"
3. Search for "Claude"
4. Click "Manage model access"
5. Select Claude model and save

## Output

The generated report includes:

- **Formatted Word Document** (.docx) matching the template format
- **Professional Narratives** describing analysis findings
- **Data Tables** with key metrics and trends
- **Appendices** with detailed unit information
- **Ready for distribution** to stakeholders

## Performance

- Template Mode: ~2-3 seconds generation time
- Claude Agent Mode: ~10-15 seconds (includes API calls to Bedrock)

## Best Practices

1. **Update PDFs Monthly** - Use latest rent roll and T12 financials
2. **Review Generated Content** - Edit narrative sections as needed
3. **Validate Numbers** - Cross-check extracted data with source documents
4. **Archive Reports** - Keep monthly reports for trending analysis
5. **Test Setup** - Run with template mode first, then upgrade to Claude Agent mode

## Advanced: Custom Prompts

To customize AI-generated narratives, edit `narrative_generator.py`:

```python
def generate_occupancy_narrative(self, occupancy_data):
    prompt = """Your custom prompt here"""
    # ...
```

## Support

For issues or feature requests:

1. Check the troubleshooting section above
2. Review AWS Bedrock documentation
3. Verify PDF source data format
4. Check AWS credentials configuration

## License

This tool is designed for property management and financial analysis. Ensure compliance with local data protection regulations when processing tenant and financial information.
