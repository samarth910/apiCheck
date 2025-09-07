#!/usr/bin/env python3

"""
KUNDLI API TEST - JSON INPUT

This script allows you to input birth details as JSON text and see the exact JSON output 
that the API will return. The output matches the response from POST /kundli endpoint.

INSTRUCTIONS:
1. Run the script
2. Paste your JSON input in the format:
   {
     "ddd": "09",
     "mmm": "10", 
     "yyyy": "1995",
     "hh": "08",
     "mm": "22",
     "place": "Samastipur"
   }
3. Press Enter twice to process
"""

import json
from kundlilabs_vPROD import main

def get_json_input():
    """Get birth details from JSON text input"""
    print("KUNDLI API TEST - JSON INPUT")
    print("=" * 60)
    print("Enter JSON input (paste your JSON, then press Enter twice):")
    print("Format: {\"ddd\": \"09\", \"mmm\": \"10\", \"yyyy\": \"1995\", \"hh\": \"08\", \"mm\": \"22\", \"place\": \"Samastipur\"}")
    print()
    
    # Read multi-line JSON input
    lines = []
    while True:
        try:
            line = input()
            if line.strip() == "":
                break
            lines.append(line)
        except EOFError:
            break
    
    json_text = "\n".join(lines)
    
    # Default JSON if no input provided
    if not json_text.strip():
        print("No input provided, using default values...")
        return {
            "ddd": "09",
            "mmm": "10", 
            "yyyy": "1995",
            "hh": "08",
            "mm": "22",
            "place": "Samastipur"
        }
    
    try:
        input_data = json.loads(json_text)
        return input_data
    except json.JSONDecodeError as e:
        print(f"Invalid JSON format: {e}")
        print("Using default values...")
        return {
            "ddd": "09",
            "mmm": "10", 
            "yyyy": "1995",
            "hh": "08",
            "mm": "22",
            "place": "Samastipur"
        }

def test_api_output():
    """Test the API and show exact output that will be returned"""
    try:
        # Get JSON input
        input_data = get_json_input()
        
        print("\n" + "=" * 60)
        print("Input Data (POST request format):")
        print(json.dumps(input_data, indent=2))
        print("\n" + "=" * 60)
        print("API Response (JSON Output):")
        print("=" * 60)
        
        # This calls the same function that the API uses
        result = main(input_data)
        
        # Print the exact JSON that the API will return
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        print("\n" + "=" * 60)
        print("SUCCESS: API test completed")
        print("=" * 60)
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_api_output()
