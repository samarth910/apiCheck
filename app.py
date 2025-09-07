from flask import Flask, jsonify, request
from kundlilabs_vPROD import main

app = Flask(__name__)

@app.route('/kundli', methods=['GET', 'POST'])
def kundli():
    try:
        if request.method == "POST":
            # Get JSON data from the request
            data_json = request.get_json()
            
            if not data_json:
                return jsonify({"error": "No JSON data provided"}), 400
            
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
