#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration module for API keys and settings
Created on: April 16, 2025
"""

import os
import sys
from dotenv import load_dotenv

# Attempt to load environment variables from .env file
load_dotenv()

# OpenAI API Configuration

def validate_api_keys():
    """Validate that API keys are available."""
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("ERROR: OPENAI_API_KEY is not set.")
        return False
    else:
        print(f"OPENAI_API_KEY is set.\n{openai_api_key}")
        return True
    
    
# validate_api_keys()