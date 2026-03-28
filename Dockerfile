# Lambda container image for Monthly Analysis Report Generator
FROM public.ecr.aws/lambda/python:3.12

WORKDIR ${LAMBDA_TASK_ROOT}

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/       ./src/
COPY api/       ./api/
COPY config/    ./config/

# Lambda handler entry point
CMD ["api.main.handler"]
