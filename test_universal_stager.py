#!/usr/bin/env python3
"""
Test script for UniversalStager
"""

import sys
sys.path.append('.')

from universal_stager_complete import UniversalStager

def test_safety_checks():
    """Test safety check functionality"""
    print("Testing UniversalStager Safety Checks")
    print("=" * 60)
    
    stager = UniversalStager()
    
    print(f"Platform: {stager.system} {stager.architecture}")
    print(f"Hostname: {stager.hostname}")
    print(f"Python: {stager.python_version}")
    
    print("\nRunning safety checks...")
    is_safe, threats = stager.run_safety_checks()
    
    print(f"\nSafety Result: {is_safe}")
    print(f"Detected Threats: {threats}")
    
    print("\nDetailed Check Results:")
    for check_name, result in stager.safety_checks.items():
        status = "PASS" if result['passed'] else "FAIL"
        print(f"  {check_name:20} : {status:6} - {result['details']}")
    
    return is_safe, threats

def test_system_fingerprint():
    """Test system fingerprint generation"""
    print("\nTesting System Fingerprint")
    print("=" * 60)
    
    stager = UniversalStager()
    fingerprint = stager._get_system_fingerprint()
    
    print(f"System Fingerprint: {fingerprint}")
    print(f"Length: {len(fingerprint)} characters")
    
    # Verify it's consistent
    fingerprint2 = stager._get_system_fingerprint()
    print(f"Consistent: {fingerprint == fingerprint2}")
    
    return fingerprint

def test_config_loading():
    """Test configuration loading"""
    print("\nTesting Configuration Loading")
    print("=" * 60)
    
    stager = UniversalStager()
    config = stager.config
    
    print("Loaded Configuration:")
    for key, value in config.items():
        if key == 'c2_urls':
            print(f"  {key:20} : {len(value)} URLs")
            for url in value[:2]:  # Show first 2
                print(f"    - {url}")
        elif isinstance(value, (int, float, bool, str)):
            print(f"  {key:20} : {value}")
        else:
            print(f"  {key:20} : {type(value).__name__}")
    
    return config

def test_verification_logic():
    """Test Stage 2 verification logic"""
    print("\nTesting Stage 2 Verification")
    print("=" * 60)
    
    stager = UniversalStager()
    
    # Test data samples
    test_cases = [
        ("Empty data", b"", False),
        ("Small data", b"x" * 500, False),
        ("Python script", b"#!/usr/bin/env python3\nimport os\nprint('Hello')", True),
        ("ELF header", b"\x7fELF" + b"x" * 100, True),
        ("PE header", b"MZ\x90\x00" + b"x" * 100, True),
        ("Mach-O header", b"\xcf\xfa\xed\xfe" + b"x" * 100, True),
        ("Rogue marker", b"rogue_implant = True", True),
    ]
    
    for name, data, expected in test_cases:
        result = stager._verify_stage2(data)
        status = "PASS" if result == expected else "FAIL"
        print(f"  {name:20} : {status:6} (expected: {expected}, got: {result})")
    
    return True

def main():
    """Run all tests"""
    print("UniversalStager Comprehensive Test Suite")
    print("=" * 60)
    
    try:
        # Run tests
        test_config_loading()
        test_system_fingerprint()
        is_safe, threats = test_safety_checks()
        test_verification_logic()
        
        print("\n" + "=" * 60)
        print("Test Summary:")
        print(f"  Environment Safe: {is_safe}")
        print(f"  Threats Detected: {len(threats)}")
        
        if threats:
            print("\n  Threat Details:")
            for threat in threats:
                print(f"    • {threat}")
        
        # Platform-specific notes
        stager = UniversalStager()
        if stager.is_windows:
            print("\n  Platform: Windows - Some checks may be limited")
        elif stager.is_linux:
            print("\n  Platform: Linux - Full check capabilities")
        elif stager.is_macos:
            print("\n  Platform: macOS - Partial check capabilities")
        
        print("\nUniversalStager test completed successfully")
        return 0
        
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())