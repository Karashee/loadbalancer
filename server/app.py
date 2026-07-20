"""
Minimal Flask web server for load balancer testing.
Provides health check and identification endpoints.
"""
import os
from flask import Flask, jsonify, Response

app = Flask(__name__)

# Read SERVER_ID from environment variable
SERVER_ID = os.environ.get('SERVER_ID', 'unknown')


@app.route('/home', methods=['GET'])
def home():
    """
    Return server identification message.
    
    Returns:
        JSON response with server ID and status
    """
    return jsonify({
        "message": f"Hello from Server: {SERVER_ID}",
        "status": "successful"
    }), 200


@app.route('/heartbeat', methods=['GET'])
def heartbeat():
    """
    Health check endpoint.
    
    Returns:
        Empty response with HTTP 200 status
    """
    return Response('', status=200, mimetype='text/plain')


if __name__ == '__main__':
    # Run server on port 5000, accessible from all interfaces
    app.run(host='0.0.0.0', port=5000, debug=False)
