"""
Vehicle Safety & Helmet Monitor WebApp Server (100% Offline - localhost only)
แสดงผลแดชบอร์ดสถานะหมวกนิรภัยและความเร็วของรถมอเตอร์ไซค์ไฟฟ้าแบบ Real-time
"""
import math
import json
import time
import os
import random
import threading
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'helmet_safety_secret_key_2026'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# สถานะรถและระบบความปลอดภัย
telemetry_state = {
    'speed': 0.0,
    'helmet': True,
    'engine_locked': False,
    'alert_count': 0,
    'is_moving': False,
    'last_updated': None
}

TELEMETRY_THREAD_RUNNING = True


@app.route('/')
def index():
    """หน้าแรก WebApp Dashboard"""
    return render_template('index.html', state=telemetry_state)


@app.route('/api/telemetry', methods=['POST'])
def receive_telemetry():
    """รับข้อมูล Real-time Telemetry จาก helmet_detection.py หรือ pc_demo.py"""
    global telemetry_state
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({'status': 'error', 'message': 'No JSON payload'}), 400

        if 'speed' in data:
            telemetry_state['speed'] = float(data['speed'])
            telemetry_state['is_moving'] = telemetry_state['speed'] > 1.0
        if 'helmet' in data:
            prev_helmet = telemetry_state['helmet']
            telemetry_state['helmet'] = bool(data['helmet'])
            if prev_helmet and not telemetry_state['helmet']:
                telemetry_state['alert_count'] += 1
        if 'engine_locked' in data:
            telemetry_state['engine_locked'] = bool(data['engine_locked'])

        telemetry_state['last_updated'] = datetime.now().strftime('%H:%M:%S')

        socketio.emit('telemetry_update', {
            'speed': round(telemetry_state['speed'], 1),
            'helmet': telemetry_state['helmet'],
            'engine_locked': telemetry_state['engine_locked'],
            'alert_count': telemetry_state['alert_count'],
            'last_updated': telemetry_state['last_updated']
        })

        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/api/status', methods=['GET'])
def get_status():
    """API ดึงสถานะปัจจุบัน"""
    return jsonify(telemetry_state)


@socketio.on('connect')
def handle_connect():
    """ส่งสถานะเริ่มต้นเมื่อมี Client เชื่อมต่อ"""
    emit('telemetry_update', {
        'speed': round(telemetry_state['speed'], 1),
        'helmet': telemetry_state['helmet'],
        'engine_locked': telemetry_state['engine_locked'],
        'alert_count': telemetry_state['alert_count'],
        'last_updated': telemetry_state['last_updated']
    })


def main():
    print("=" * 60)
    print(" 🛵 Vehicle Safety & Helmet Monitor Server (100% Offline)")
    print(" URL: http://localhost:5000")
    print("=" * 60)
    try:
        socketio.run(app, host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\n[INFO] ปิด WebApp Server...")


if __name__ == '__main__':
    main()
