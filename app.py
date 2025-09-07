from flask import Flask, jsonify, request
from kundlilabs_vPROD import main

app = Flask(__name__)

@app.route('/kundli', methods=['GET', 'POST'])
def kundli():
    try:
        if request.method == "POST":
            # Check content type
            if not request.is_json:
                return jsonify({
                    "error": "Content-Type must be application/json",
                    "received_content_type": request.content_type
                }), 400
            
            # Debug: Log the raw request data
            raw_data = request.get_data(as_text=True)
            print(f"Raw request data: {raw_data}")
            
            # Get JSON data from the request
            try:
                data_json = request.get_json()
            except Exception as json_error:
                # Try to fix common JSON issues and parse again
                try:
                    import re
                    import json
                    
                    fixed_data = raw_data
                    
                    # Fix 1: Remove leading zeros from numbers (e.g., 00 -> 0)
                    fixed_data = re.sub(r':\s*0+(\d+)', r': \1', fixed_data)
                    
                    # Fix 2: Handle standalone 00 -> 0
                    fixed_data = re.sub(r':\s*00(?=\s*[,}])', r': 0', fixed_data)
                    
                    # Fix 3: Add quotes around unquoted string values
                    # Matches: "key": value (where value starts with letter and is not quoted)
                    pattern = r':\s*([a-zA-Z][a-zA-Z0-9\s]*?)(?=\s*[,}])'
                    fixed_data = re.sub(pattern, r': "\1"', fixed_data)
                    
                    # Fix 4: Handle trailing commas
                    fixed_data = re.sub(r',(\s*[}\]])', r'\1', fixed_data)
                    
                    print(f"Attempting to fix JSON. Original: {raw_data}")
                    print(f"Fixed JSON: {fixed_data}")
                    
                    data_json = json.loads(fixed_data)
                    print(f"Successfully parsed fixed JSON: {data_json}")
                    
                except Exception as fix_error:
                    return jsonify({
                        "error": "Invalid JSON format - could not auto-fix",
                        "original_error": str(json_error),
                        "fix_attempt_error": str(fix_error),
                        "raw_data": raw_data,
                        "common_issue": "Check if string values like place names have quotes around them"
                    }), 400
            
            print(f"Parsed JSON: {data_json}")
            
            if not data_json:
                return jsonify({
                    "error": "No JSON data provided or empty JSON",
                    "raw_data": raw_data
                }), 400
            
            # Check for Voiceflow template variables
            for key, value in data_json.items():
                if isinstance(value, str) and "variableID" in str(value):
                    return jsonify({
                        "error": "Voiceflow template variables detected. Please ensure variables are properly resolved before sending to API.",
                        "received_data": data_json,
                        "issue": f"Field '{key}' contains template variable: {value}"
                    }), 400
            
            # Validate required fields
            required_fields = ['ddd', 'mmm', 'yyyy', 'hh', 'mm', 'place']
            missing_fields = [field for field in required_fields if field not in data_json]
            
            if missing_fields:
                return jsonify({
                    "error": f"Missing required fields: {', '.join(missing_fields)}",
                    "required_fields": required_fields,
                    "received_data": data_json
                }), 400
            
            # Call main function with birth data
            result = main(data_json)
            
            # Debug: Print the result being sent back
            print(f"=== VEDIC CHART SUMMARY - OUTPUT ===")
            print(f"Birth Data Input: {data_json}")
            print(f"Result Type: {type(result)}")
            print(f"Result Keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
            
            if isinstance(result, dict):
                if 'birth_info' in result:
                    print(f"Birth Info: {result['birth_info']}")
                if 'lagna' in result:
                    print(f"Lagna: {result['lagna']}")
                if 'houses' in result:
                    print(f"Number of Houses: {len(result['houses'])}")
                    for i, house in enumerate(result['houses'][:3]):  # Show first 3 houses
                        print(f"House {i+1}: {house}")
                if 'error' in result:
                    print(f"ERROR in result: {result['error']}")
            
            print(f"=== END VEDIC CHART SUMMARY ===")
            
            # Check if there was an error in the calculation
            if "error" in result:
                return jsonify(result), 500
            
            final_response = {
                "success": True,
                "kundli_data": result
            }
            
            # Debug: Print final response
            print(f"Final API Response: {final_response}")
            
            return jsonify(final_response)
        
        else:
            # For GET requests, use static values
            result = main()
            return jsonify({
                "success": True,
                "kundli_data": result,
                "note": "Using static birth data for GET request"
            })
            
    except Exception as e:
        return jsonify({
            "error": f"Server error: {str(e)}",
            "success": False
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "Kundli Labs API",
        "version": "1.0"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
