from flask import Flask, jsonify
from kundlilabs_vPROD import main

app = Flask(__name__)

@app.route('/kundli', methods=['GET'])
def get_kundli():
    import io
    import sys

    buffer = io.StringIO()
    sys.stdout = buffer
    try:
        main()
    except Exception as e:
        return jsonify({"error": str(e)})
    finally:
        sys.stdout = sys.__stdout__
    
    result = buffer.getvalue()
    return jsonify({"output": result})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
