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
                return jsonify({
                    "error": "Invalid JSON format",
                    "details": str(json_error),
                    "raw_data": raw_data
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
            
            # Check if there was an error in the calculation
            if "error" in result:
                return jsonify(result), 500
            
            return jsonify({
                "success": True,
                "kundli_data": result
            })
        
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
