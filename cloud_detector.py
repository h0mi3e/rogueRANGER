#!/usr/bin/env python3
"""
Cloud Environment Detector for rogueRANGER Phase 2
Advanced cloud provider detection and environment adaptation
"""

import os
import sys
import json
import socket
import urllib.request
import urllib.error
import time
import hashlib
import subprocess
import platform
import re
from typing import Dict, List, Optional, Tuple, Any
import ssl

class CloudDetector:
    """
    Comprehensive cloud environment detection and adaptation
    Detects: AWS, Azure, GCP, Oracle Cloud, DigitalOcean, Alibaba Cloud
    Provides environment-specific adaptation recommendations
    """
    
    def __init__(self, timeout: int = 5):
        self.timeout = timeout
        self.detection_results = {}
        self.confidence_scores = {}
        self.environment_type = "unknown"
        self.cloud_provider = "unknown"
        self.metadata = {}
        
        # Cloud-specific metadata endpoints
        self.cloud_endpoints = {
            'aws': {
                'metadata_url': 'http://169.254.169.254/latest/meta-data/',
                'signature_url': 'http://169.254.169.254/latest/dynamic/instance-identity/document',
                'indicators': [
                    '/sys/hypervisor/uuid',  # AWS Xen hypervisor
                    '/sys/devices/virtual/dmi/id/product_version',  # Contains 'amazon'
                    '/sys/devices/virtual/dmi/id/bios_version',  # Contains 'amazon'
                    '/sys/class/dmi/id/chassis_asset_tag',  # Contains 'Amazon'
                ]
            },
            'azure': {
                'metadata_url': 'http://169.254.169.254/metadata/instance?api-version=2021-02-01',
                'headers': {'Metadata': 'true'},
                'indicators': [
                    '/sys/class/dmi/id/chassis_asset_tag',  # Contains '7783-7084-3265-9085-8269'
                    '/sys/class/dmi/id/sys_vendor',  # Contains 'Microsoft Corporation'
                ]
            },
            'gcp': {
                'metadata_url': 'http://metadata.google.internal/computeMetadata/v1/',
                'headers': {'Metadata-Flavor': 'Google'},
                'indicators': [
                    '/sys/class/dmi/id/product_name',  # Contains 'Google Compute Engine'
                    '/sys/class/dmi/id/bios_vendor',  # Contains 'Google'
                ]
            },
            'oracle': {
                'metadata_url': 'http://169.254.169.254/opc/v1/instance/',
                'indicators': [
                    '/sys/class/dmi/id/chassis_asset_tag',  # Contains 'OracleCloud'
                    '/sys/class/dmi/id/product_name',  # Contains 'Oracle Cloud'
                ]
            },
            'digitalocean': {
                'metadata_url': 'http://169.254.169.254/metadata/v1.json',
                'indicators': [
                    '/sys/class/dmi/id/product_name',  # Contains 'DigitalOcean'
                    '/sys/class/dmi/id/sys_vendor',  # Contains 'DigitalOcean'
                ]
            },
            'alibaba': {
                'metadata_url': 'http://100.100.100.200/latest/meta-data/',
                'indicators': [
                    '/sys/class/dmi/id/product_name',  # Contains 'Alibaba Cloud'
                    '/sys/class/dmi/id/sys_vendor',  # Contains 'Alibaba Cloud'
                ]
            }
        }
        
        # SSL context for HTTPS requests
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
    
    def detect_all(self) -> Dict[str, Any]:
        """
        Run comprehensive cloud environment detection
        Returns: Complete detection results with confidence scores
        """
        print("[CLOUD DETECT] Starting comprehensive cloud environment analysis")
        
        # Reset results
        self.detection_results = {}
        self.confidence_scores = {}
        
        # Run detection methods
        methods = [
            self._detect_via_metadata,
            self._detect_via_filesystem,
            self._detect_via_network,
            self._detect_via_system_commands,
            self._detect_via_environment_vars
        ]
        
        for method in methods:
            try:
                method()
            except Exception as e:
                print(f"[CLOUD DETECT] Error in {method.__name__}: {e}")
        
        # Analyze results and determine environment
        self._analyze_results()
        
        return {
            'environment_type': self.environment_type,
            'cloud_provider': self.cloud_provider,
            'confidence_scores': self.confidence_scores,
            'detection_results': self.detection_results,
            'metadata': self.metadata,
            'recommendations': self._generate_recommendations()
        }
    
    def _detect_via_metadata(self):
        """Detect cloud provider via metadata APIs"""
        print("[CLOUD DETECT] Checking cloud metadata endpoints...")
        
        for provider, config in self.cloud_endpoints.items():
            try:
                url = config.get('metadata_url')
                headers = config.get('headers', {})
                
                req = urllib.request.Request(url, headers=headers)
                
                with urllib.request.urlopen(req, timeout=self.timeout, context=self.ssl_context) as response:
                    if response.getcode() == 200:
                        content = response.read().decode('utf-8')
                        
                        # Parse JSON if possible
                        try:
                            metadata = json.loads(content)
                            self.metadata[provider] = metadata
                            print(f"[CLOUD DETECT] Found {provider.upper()} metadata")
                            self._add_detection(provider, 'metadata_api', 0.9)
                        except json.JSONDecodeError:
                            # Some metadata endpoints return plain text
                            if provider == 'aws' and 'instance-id' in content:
                                self._add_detection(provider, 'metadata_api', 0.8)
                            else:
                                self._add_detection(provider, 'metadata_api', 0.7)
                        
            except urllib.error.URLError:
                # Expected for non-matching providers
                pass
            except Exception as e:
                print(f"[CLOUD DETECT] Error checking {provider}: {e}")
    
    def _detect_via_filesystem(self):
        """Detect cloud provider via filesystem indicators"""
        print("[CLOUD DETECT] Checking filesystem indicators...")
        
        for provider, config in self.cloud_endpoints.items():
            indicators = config.get('indicators', [])
            provider_score = 0
            
            for indicator_path in indicators:
                if os.path.exists(indicator_path):
                    try:
                        with open(indicator_path, 'r') as f:
                            content = f.read().lower()
                            
                        # Check for provider-specific strings
                        provider_keywords = {
                            'aws': ['amazon', 'ec2', 'aws'],
                            'azure': ['microsoft', 'azure'],
                            'gcp': ['google', 'gce', 'google compute engine'],
                            'oracle': ['oracle', 'oraclecloud'],
                            'digitalocean': ['digitalocean'],
                            'alibaba': ['alibaba', 'alibaba cloud']
                        }
                        
                        keywords = provider_keywords.get(provider, [])
                        for keyword in keywords:
                            if keyword in content:
                                provider_score += 0.3
                                print(f"[CLOUD DETECT] Found {provider.upper()} indicator: {indicator_path}")
                                break
                                
                    except Exception as e:
                        print(f"[CLOUD DETECT] Error reading {indicator_path}: {e}")
            
            if provider_score > 0:
                self._add_detection(provider, 'filesystem', min(provider_score, 0.9))
    
    def _detect_via_network(self):
        """Detect cloud environment via network characteristics"""
        print("[CLOUD DETECT] Analyzing network configuration...")
        
        # Check for cloud-specific DNS
        try:
            with open('/etc/resolv.conf', 'r') as f:
                resolv_conf = f.read()
            
            cloud_dns_patterns = {
                'aws': [r'169\.254\.169\.253', r'AmazonDNS'],
                'azure': [r'168\.63\.129\.16', r'AzureDNS'],
                'gcp': [r'169\.254\.169\.254', r'Google'],
                'oracle': [r'169\.254\.169\.254'],
                'digitalocean': [r'67\.207\.67\.2', r'67\.207\.67\.3']
            }
            
            for provider, patterns in cloud_dns_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, resolv_conf):
                        self._add_detection(provider, 'dns_config', 0.7)
                        print(f"[CLOUD DETECT] Found {provider.upper()} DNS pattern")
                        break
                        
        except Exception as e:
            print(f"[CLOUD DETECT] Error reading DNS config: {e}")
        
        # Check hostname for cloud patterns
        try:
            hostname = socket.gethostname()
            cloud_hostname_patterns = {
                'aws': [r'ip-\d+-\d+-\d+-\d+', r'ec2-\d+-\d+-\d+-\d+'],
                'azure': [r'^[a-z0-9]{12}$', r'vm-\d+'],  # Azure VM names
                'gcp': [r'\.internal$', r'\.c\.PROJECT_ID\.internal$'],
            }
            
            for provider, patterns in cloud_hostname_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, hostname, re.IGNORECASE):
                        self._add_detection(provider, 'hostname', 0.6)
                        print(f"[CLOUD DETECT] Found {provider.upper()} hostname pattern: {hostname}")
                        break
                        
        except Exception as e:
            print(f"[CLOUD DETECT] Error analyzing hostname: {e}")
    
    def _detect_via_system_commands(self):
        """Detect cloud environment via system command output"""
        print("[CLOUD DETECT] Running system command checks...")
        
        # Check for cloud-init (common in cloud VMs)
        try:
            result = subprocess.run(
                ['which', 'cloud-init'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                self._add_detection('generic_cloud', 'cloud_init', 0.5)
                print("[CLOUD DETECT] Found cloud-init (generic cloud indicator)")
                
                # Check cloud-init config for provider hints
                try:
                    with open('/etc/cloud/cloud.cfg', 'r') as f:
                        cloud_cfg = f.read()
                    
                    if 'datasource_list' in cloud_cfg:
                        if 'Ec2' in cloud_cfg:
                            self._add_detection('aws', 'cloud_config', 0.8)
                        elif 'Azure' in cloud_cfg:
                            self._add_detection('azure', 'cloud_config', 0.8)
                        elif 'GCE' in cloud_cfg or 'Google' in cloud_cfg:
                            self._add_detection('gcp', 'cloud_config', 0.8)
                except:
                    pass
                    
        except Exception as e:
            print(f"[CLOUD DETECT] Error checking cloud-init: {e}")
        
        # Check for virtualization (cloud VMs are virtualized)
        try:
            # Check via systemd-detect-virt if available
            result = subprocess.run(
                ['systemd-detect-virt'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                virt_type = result.stdout.strip().lower()
                if virt_type not in ['none', '']:
                    self._add_detection('generic_cloud', 'virtualization', 0.4)
                    print(f"[CLOUD DETECT] Virtualization detected: {virt_type}")
                    
        except Exception as e:
            print(f"[CLOUD DETECT] Error checking virtualization: {e}")
    
    def _detect_via_environment_vars(self):
        """Detect cloud environment via environment variables"""
        print("[CLOUD DETECT] Checking environment variables...")
        
        # Common cloud environment variables
        cloud_env_vars = {
            'aws': ['AWS_', 'EC2_'],
            'azure': ['AZURE_', 'ARM_'],
            'gcp': ['GOOGLE_', 'GCP_', 'CLOUDSDK_'],
            'oracle': ['OCI_'],
            'digitalocean': ['DIGITALOCEAN_'],
            'alibaba': ['ALIBABA_', 'ACS_']
        }
        
        for provider, prefixes in cloud_env_vars.items():
            for env_key, env_value in os.environ.items():
                for prefix in prefixes:
                    if env_key.startswith(prefix):
                        self._add_detection(provider, 'environment_vars', 0.8)
                        print(f"[CLOUD DETECT] Found {provider.upper()} env var: {env_key}")
                        break
    
    def _add_detection(self, provider: str, method: str, confidence: float):
        """Add detection result with confidence score"""
        if provider not in self.detection_results:
            self.detection_results[provider] = {}
        
        self.detection_results[provider][method] = confidence
        
        # Update confidence score
        if provider not in self.confidence_scores:
            self.confidence_scores[provider] = 0
        
        # Weight different detection methods
        method_weights = {
            'metadata_api': 1.0,
            'filesystem': 0.9,
            'cloud_config': 0.8,
            'environment_vars': 0.7,
            'dns_config': 0.6,
            'hostname': 0.5,
            'virtualization': 0.4,
            'cloud_init': 0.3
        }
        
        weight = method_weights.get(method, 0.5)
        self.confidence_scores[provider] += confidence * weight
    
    def _analyze_results(self):
        """Analyze detection results and determine environment"""
        print("[CLOUD DETECT] Analyzing detection results...")
        
        # Find provider with highest confidence
        if self.confidence_scores:
            sorted_providers = sorted(
                self.confidence_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            top_provider, top_score = sorted_providers[0]
            
            # Determine if we're in a cloud environment
            if top_score >= 0.5:
                self.cloud_provider = top_provider
                self.environment_type = "cloud"
                print(f"[CLOUD DETECT] Detected {top_provider.upper()} cloud environment (confidence: {top_score:.2f})")
            elif top_score >= 0.3:
                self.environment_type = "likely_cloud"
                print(f"[CLOUD DETECT] Likely cloud environment (confidence: {top_score:.2f})")
            else:
                self.environment_type = "on_prem"
                print(f"[CLOUD DETECT] On-premises or unknown environment")
        else:
            self.environment_type = "on_prem"
            print("[CLOUD DETECT] No cloud indicators found")
    
    def _generate_recommendations(self) -> Dict[str, Any]:
        """Generate environment-specific recommendations"""
        recommendations = {
            'general': [],
            'c2_channels': [],
            'evasion_techniques': [],
            'operational_considerations': []
        }
        
        if self.environment_type == "cloud":
            # Cloud-specific recommendations
            recommendations['general'].append(f"Adapt behavior for {self.cloud_provider.upper()} environment")
            recommendations['general'].append("Use cloud-native services for C2 where possible")
            recommendations['general'].append("Leverage instance metadata for fingerprinting")
            
            # Provider-specific C2 channels
            c2_channels = {
                'aws': ['S3 buckets', 'Lambda functions', 'SQS queues'],
                'azure': ['Azure Blob Storage', 'Azure Functions', 'Service Bus'],
                'gcp': ['Cloud Storage', 'Cloud Functions', 'Pub/Sub'],
                'oracle': ['Object Storage', 'Functions'],
                'digitalocean': ['Spaces', 'Functions'],
                'alibaba': ['OSS', 'Function Compute']
            }
            
            provider_channels = c2_channels.get(self.cloud_provider, [])
            recommendations['c2_channels'].extend(provider_channels)
            
            # Cloud evasion techniques
            recommendations['evasion_techniques'].append("Blend in with legitimate cloud traffic")
            recommendations['evasion_techniques'].append("Use cloud service APIs for communication")
            recommendations['evasion_techniques'].append("Avoid triggering cloud security services")
            
            # Operational considerations
            recommendations['operational_considerations'].append("Be aware of cloud logging and monitoring")
            recommendations['operational_considerations'].append("Consider cloud region and compliance requirements")
            recommendations['operational_considerations'].append("Use ephemeral resources to avoid persistence detection")
            
        elif self.environment_type == "on_prem":
            # On-premises recommendations
            recommendations['general'].append("Standard enterprise security controls expected")
            recommendations['general'].append("Higher likelihood of EDR/AV solutions")
            
            recommendations['c2_channels'].append("HTTPS to external domains")
            recommendations['c2_channels'].append("DNS tunneling")
            recommendations['c2_channels'].append("ICMP/other protocol tunneling")
            
            recommendations['evasion_techniques'].append("Process hollowing into legitimate binaries")
            recommendations['evasion_techniques'].append("Memory-only execution")
            recommendations['evasion_techniques'].append("Heavy obfuscation and packing")
            recommendations['evasion_techniques'].append("Living-off-the-land binaries (LOLBAS)")
            
            recommendations['operational_considerations'].append("Assume network monitoring and IDS/IPS")
            recommendations['operational_considerations'].append("Consider air-gapped network possibilities")
            recommendations['operational_considerations'].append("Higher risk of manual investigation")
        
        return recommendations
    
    def get_environment_summary(self) -> Dict[str, Any]:
        """Get concise environment summary"""
        return {
            'environment_type': self.environment_type,
            'cloud_provider': self.cloud_provider,
            'confidence_scores': self.confidence_scores,
            'is_cloud': self.environment_type in ["cloud", "likely_cloud"],
            'is_on_prem': self.environment_type == "on_prem",
            'provider_confidence': max(self.confidence_scores.values()) if self.confidence_scores else 0
        }
    
    def should_enable_cloud_features(self, threshold: float = 0.5) -> bool:
        """Determine if cloud-specific features should be enabled"""
        if self.environment_type == "cloud":
            return True
        elif self.environment_type == "likely_cloud" and threshold <= 0.4:
            return True
        return False
    
    def get_optimal_c2_channels(self) -> List[str]:
        """Get recommended C2 channels for current environment"""
        if self.environment_type == "cloud":
            # Cloud-native channels
            channels = {
                'aws': ['s3', 'lambda', 'sqs', 'sns'],
                'azure': ['blob_storage', 'functions', 'service_bus'],
                'gcp': ['cloud_storage', 'cloud_functions', 'pubsub'],
                'oracle': ['object_storage', 'functions'],
                'digitalocean': ['spaces', 'functions'],
                'alibaba': ['oss', 'function_compute']
            }
            return channels.get(self.cloud_provider, ['https', 'dns'])
        else:
            # On-prem channels
            return ['https', 'dns', 'icmp', 'social_media']
    
    def get_evasion_recommendations(self) -> List[str]:
        """Get environment-specific evasion recommendations"""
        if self.environment_type == "cloud":
            return [
                "Use cloud service APIs for blending",
                "Leverage instance metadata for authentication",
                "Avoid triggering cloud security alerts",
                "Use ephemeral resources",
                "Encrypt all cloud API calls"
            ]
        else:
            return [
                "Process injection and hollowing",
                "Memory-only execution",
                "Heavy obfuscation",
                "LOLBAS usage",
                "Minimal disk footprint",
                "Encrypted communications"
            ]

def main():
    """Test function"""
    print("[CLOUD DETECTOR] Starting test...")
    detector = CloudDetector()
    results = detector.detect_all()
    
    print(f"\nEnvironment: {results['environment_type']}")
    print(f"Provider: {results['cloud_provider']}")
    print(f"Cloud Features Enabled: {detector.should_enable_cloud_features()}")
    print(f"Optimal C2 Channels: {', '.join(detector.get_optimal_c2_channels())}")
    
    return results

if __name__ == "__main__":
    main()