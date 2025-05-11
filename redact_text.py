#!/usr/bin/env python3
"""
Simple script to test the redaction functionality.
"""
import argparse
import requests
import json
import sys

def redact_text(text):
    """Send text to the redaction API and return the redacted version."""
    url = "http://localhost:6366/redact_text"
    
    data = {
        "text": text
    }
    
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            result = response.json()
            redacted_text = result.get('redacted_text', '')
            return redacted_text
        else:
            print(f"Error: Server returned status code {response.status_code}")
            print(response.text)
            return text
            
    except Exception as e:
        print(f"Error connecting to server: {str(e)}")
        return text

def main():
    parser = argparse.ArgumentParser(description='Redact sensitive information from text.')
    parser.add_argument('text', nargs='?', help='Text to redact. If not provided, will read from stdin.')
    
    args = parser.parse_args()
    
    # Get text from command line argument or stdin
    if args.text:
        text = args.text
    else:
        text = sys.stdin.read()
    
    # Redact the text
    redacted = redact_text(text)
    
    # Print the redacted text
    print(redacted)

if __name__ == "__main__":
    main()