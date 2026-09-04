"""
GPS Geofence WebApp Server (100% Offline - localhost only)
เปิด Browser ที่ http://localhost:5000 บนเครื่องเดียวกัน ไม่ต้องใช้ WiFi หรือ Internet
"""
import threading
import time
import math
import random
import webbrowser
import os
import sys

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO

# เพิ่ม parent directory เข้า path เพื่อ import geofence module
sys.path.insert(0, os.path.dirname(__file__))
from geofence import CircleGeofence, GeofenceAlertLogger

app = Flask(__name__)
app.config['SECRET_KEY'] = 'helmet-geofence-offline'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ========== Geofence State ==========
geofence = CircleGeofence(
    center_lat=13.756331,
    center_lon=100.501765,
    radius_m=500
)
alert_logger = GeofenceAlertLogger(
    log_dir=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
)

# ========== GPS Simulation State (สำหรับทดสอบบน PC) ==========
gps_state = {
    'lat': 13.756331,
    'lon': 100.501765,
    'speed': 0.0,
    'satellites': 9,
    'heading': 45.0,   # ทิศทางเป็นองศา (0=เหนือ, 90=ตะวันออก)
    'is_moving': False,
    'helmet': True,
    'trail': [],
    'was_outside': False,
    'alert_count': 0
}

GPS_THREAD_RUNNING = True


def simulate_gps_movement():
    """Thread จำลองการเคลื่อนที่ GPS (สำหรับ PC Demo)"""
    global GPS_THREAD_RUNNING

    while GPS_THREAD_RUNNING:
        time.sleep(0.5)

        if gps_state['is_moving']:
            # จำลองการเคลื่อนที่ไปในทิศทางที่กำหนด
            speed_ms = gps_state['speed'] / 3.6   # km/h -> m/s
            distance_m = speed_ms * 0.5            # ระยะที่เคลื่อนที่ใน 0.5 วินาที

            heading_rad = math.radians(gps_state['heading'])
            # 1 degree latitude ≈ 111,320 m
            dlat = (distance_m * math.cos(heading_rad)) / 111320.0
            # 1 degree longitude ≈ 111,320 * cos(lat) m
            dlon = (distance_m * math.sin(heading_rad)) / (111320.0 * math.cos(math.radians(gps_state['lat'])))

            gps_state['lat'] += dlat
            gps_state['lon'] += dlon

            # สุ่มเบี่ยงทิศเล็กน้อย
            gps_state['heading'] += random.uniform(-3, 3)
            gps_state['heading'] %= 360

        # ตรวจสอบ Geofence
        dist_to_center = geofence.distance_to_center(gps_state['lat'], gps_state['lon'])
        is_inside = geofence.is_inside(gps_state['lat'], gps_state['lon'])
        dist_to_boundary = geofence.distance_to_boundary(gps_state['lat'], gps_state['lon'])

        # ตรวจจับว่าเพิ่งออกนอกเขต (เพื่อบันทึก log ไม่ซ้ำ)
        if not is_inside and not gps_state['was_outside']:
            gps_state['alert_count'] += 1
            alert_logger.log_alert(
                gps_state['lat'], gps_state['lon'],
                gps_state['speed'], dist_to_center, geofence
            )
        gps_state['was_outside'] = not is_inside

        # เก็บเส้นทาง Trail (จำกัด 500 จุดล่าสุด)
        gps_state['trail'].append({'lat': gps_state['lat'], 'lon': gps_state['lon']})
        if len(gps_state['trail']) > 500:
            gps_state['trail'] = gps_state['trail'][-500:]

        # ส่งข้อมูลไปยัง Browser ผ่าน WebSocket
        socketio.emit('gps_update', {
            'lat': round(gps_state['lat'], 6),
            'lon': round(gps_state['lon'], 6),
            'speed': round(gps_state['speed'], 1),
            'satellites': gps_state['satellites'],
            'heading': round(gps_state['heading'], 1),
            'helmet': gps_state['helmet'],
            'is_inside': is_inside,
            'dist_to_center': round(dist_to_center, 1),
            'dist_to_boundary': round(dist_to_boundary, 1),
            'alert_count': gps_state['alert_count'],
            'trail': gps_state['trail'][-200:]   # ส่ง 200 จุดล่าสุด
        })


# ========== Routes ==========

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/geofence', methods=['GET'])
def get_geofence():
    return jsonify(geofence.to_dict())


@app.route('/api/geofence', methods=['POST'])
def set_geofence():
    data = request.get_json()
    geofence.update(
        float(data.get('center_lat', geofence.center_lat)),
        float(data.get('center_lon', geofence.center_lon)),
        float(data.get('radius_m', geofence.radius_m))
    )
    gps_state['was_outside'] = False
    return jsonify({'status': 'ok', **geofence.to_dict()})


@app.route('/api/set_center_here', methods=['POST'])
def set_center_here():
    """ตั้งจุดศูนย์กลาง Geofence ณ ตำแหน่งปัจจุบันของรถ"""
    geofence.update(gps_state['lat'], gps_state['lon'], geofence.radius_m)
    gps_state['was_outside'] = False
    return jsonify({'status': 'ok', **geofence.to_dict()})


# ========== WebSocket Controls (สำหรับ Demo) ==========

@socketio.on('demo_start_moving')
def handle_start(data):
    gps_state['is_moving'] = True
    gps_state['speed'] = float(data.get('speed', 30))
    gps_state['heading'] = float(data.get('heading', gps_state['heading']))


@socketio.on('demo_stop')
def handle_stop(_=None):
    gps_state['is_moving'] = False
    gps_state['speed'] = 0.0


@socketio.on('demo_set_heading')
def handle_heading(data):
    gps_state['heading'] = float(data.get('heading', 0))


@socketio.on('demo_toggle_helmet')
def handle_helmet(_=None):
    gps_state['helmet'] = not gps_state['helmet']


@socketio.on('demo_reset')
def handle_reset(_=None):
    gps_state['lat'] = geofence.center_lat
    gps_state['lon'] = geofence.center_lon
    gps_state['speed'] = 0.0
    gps_state['is_moving'] = False
    gps_state['trail'] = []
    gps_state['was_outside'] = False
    gps_state['alert_count'] = 0
    gps_state['heading'] = 45.0


# ========== Main ==========

def main():
    global GPS_THREAD_RUNNING

    print("=" * 60)
    print(" 🛰️  GPS Geofence Monitor (100% Offline)")
    print("=" * 60)
    print(f" Geofence: วงกลมรัศมี {geofence.radius_m} เมตร")
    print(f" ศูนย์กลาง: {geofence.center_lat:.6f}, {geofence.center_lon:.6f}")
    print(f" WebApp: http://localhost:5000")
    print("=" * 60)

    # เริ่ม Thread จำลอง GPS
    gps_thread = threading.Thread(target=simulate_gps_movement, daemon=True)
    gps_thread.start()

    # เปิด Browser อัตโนมัติ
    threading.Timer(1.5, lambda: webbrowser.open('http://localhost:5000')).start()

    try:
        socketio.run(app, host='127.0.0.1', port=5000, debug=False, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        pass
    finally:
        GPS_THREAD_RUNNING = False
        print("\n[INFO] ปิดระบบ Geofence Monitor")


if __name__ == '__main__':
    main()
