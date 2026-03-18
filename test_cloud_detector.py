#!/usr/bin/env python3
"""
Test script for CloudDetector
"""

import sys
sys.path.append('.')

from cloud_detector import CloudDetector

def main():
    print("🚀 Testing CloudDetector - Phase 2 Foundation")
    print("=" * 60)
    
    # Create detector
    detector = CloudDetector(timeout=3)
    
    # Run detection
    print("\n[1] Running comprehensive cloud detection...")
    results = detector.detect_all()
    
    print("\n[2] Detection Results:")
    print("-" * 40)
    print(f"Environment Type: {results['environment_type']}")
    print(f"Cloud Provider: {results['cloud_provider']}")
    
    print("\n[3] Confidence Scores:")
    print("-" * 40)
    for provider, score in results['confidence_scores'].items():
        print(f"  {provider.upper():15} : {score:.3f}")
    
    print("\n[4] Detection Methods:")
    print("-" * 40)
    for provider, methods in results['detection_results'].items():
        print(f"\n  {provider.upper()}:")
        for method, confidence in methods.items():
            print(f"    • {method:20} : {confidence:.2f}")
    
    print("\n[5] Recommendations:")
    print("-" * 40)
    for category, recs in results['recommendations'].items():
        if recs:
            print(f"\n  {category.replace('_', ' ').title()}:")
            for rec in recs:
                print(f"    • {rec}")
    
    print("\n[6] Metadata Collected:")
    print("-" * 40)
    if results['metadata']:
        for provider, metadata in results['metadata'].items():
            print(f"\n  {provider.upper()}:")
            if isinstance(metadata, dict):
                for key, value in list(metadata.items())[:3]:  # Show first 3 items
                    print(f"    • {key}: {str(value)[:50]}...")
            else:
                print(f"    • Raw metadata: {str(metadata)[:100]}...")
    else:
        print("  No metadata collected (not in cloud or endpoints blocked)")
    
    print("\n" + "=" * 60)
    print("CloudDetector Test Complete!")
    
    # Environment summary
    env_type = results['environment_type']
    provider = results['cloud_provider']
    
    if env_type == "cloud":
        print(f"✅ Detected {provider.upper()} cloud environment")
        print("   Phase 2 cloud-aware evasion will be enabled")
    elif env_type == "likely_cloud":
        print("⚠️  Likely cloud environment detected")
        print("   Phase 2 features will use cautious approach")
    else:
        print("✅ On-premises environment detected")
        print("   Phase 2 will use standard enterprise evasion")
    
    return results

if __name__ == "__main__":
    main()