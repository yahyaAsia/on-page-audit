#!/bin/bash

echo "Setting up the On-Page SEO Audit tool..."

# Create a virtual environment (optional)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

echo "Setup complete! Run the tool using: streamlit run seo_audit.py"
