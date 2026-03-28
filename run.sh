#!/bin/bash
# Launch script for the Monthly Analysis Report Generator
# Usage:
#   ./run.sh                                    (uses default data paths)
#   ./run.sh --rent-roll path/to/rr.pdf --financials path/to/t12.pdf --output path/to/out.docx

set -e

# Activate pyenv virtualenv
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
pyenv activate realsi

# Run from project root so 'src' package resolves correctly
cd "$(dirname "$0")"

python run.py "$@"
