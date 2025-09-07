from flask import Flask, jsonify, request
from kundlilabs_vPROD import main

app = Flask(__name__)

@app.route('/kundli', methods=['GET', 'POST'])
def kundli():
    import io
    import sys

    # Capture stdout from main()
    buffer = io.StringIO()
    sys.stdout = buffer

    # For POST, get JSON from request
    if request.method == "POST":
        data_json = request.get_json()
    else:
        data_json = None  # or default values

    try:
        # Pass data_json to main() if your main function supports it
        if data_json:
            main(data_json)
        else:
            main()
    except Exception as e:
        return jsonify({"error": str(e)})
    finally:
        sys.stdout = sys.__stdout__

    result = buffer.getvalue()
    return jsonify({"output": result})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
