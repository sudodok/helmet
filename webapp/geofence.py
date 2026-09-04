"""
Geofencing Module - ระบบกำหนดเขตพื้นที่แบบวงกลม (Circle Geofence)
ใช้สูตร Haversine คำนวณระยะทางบนพื้นโลกทรงกลม ทำงาน 100% Offline
"""
import math
import json
import os
from datetime import datetime

# รัศมีโลกเฉลี่ย (เมตร)
EARTH_RADIUS_M = 6_371_000


def haversine_distance(lat1, lon1, lat2, lon2):
    """คำนวณระยะทางระหว่าง 2 จุดบนผิวโลก (เมตร) ด้วยสูตร Haversine"""
    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)

    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS_M * c


class CircleGeofence:
    """เขตพื้นที่แบบวงกลม กำหนดจุดศูนย์กลาง + รัศมี (เมตร)"""

    def __init__(self, center_lat=13.756331, center_lon=100.501765, radius_m=500):
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.radius_m = radius_m

    def is_inside(self, lat, lon):
        """ตรวจสอบว่าจุด (lat, lon) อยู่ภายในเขตหรือไม่"""
        dist = haversine_distance(self.center_lat, self.center_lon, lat, lon)
        return dist <= self.radius_m

    def distance_to_center(self, lat, lon):
        """คำนวณระยะห่างจากจุดศูนย์กลาง (เมตร)"""
        return haversine_distance(self.center_lat, self.center_lon, lat, lon)

    def distance_to_boundary(self, lat, lon):
        """ระยะห่างจากขอบเขตวงกลม (เมตร) ค่าบวก=อยู่ในเขต ค่าลบ=นอกเขต"""
        return self.radius_m - self.distance_to_center(lat, lon)

    def to_dict(self):
        return {
            'center_lat': self.center_lat,
            'center_lon': self.center_lon,
            'radius_m': self.radius_m
        }

    def update(self, center_lat, center_lon, radius_m):
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.radius_m = radius_m


class GeofenceAlertLogger:
    """บันทึกประวัติการออกนอกเขต Geofence ลงไฟล์ JSON"""

    def __init__(self, log_dir='logs'):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.alerts = []

    def log_alert(self, lat, lon, speed, distance_m, geofence):
        alert = {
            'timestamp': datetime.now().isoformat(),
            'latitude': round(lat, 6),
            'longitude': round(lon, 6),
            'speed_kmh': round(speed, 1),
            'distance_from_center_m': round(distance_m, 1),
            'geofence_radius_m': geofence.radius_m,
            'geofence_center': {
                'lat': geofence.center_lat,
                'lon': geofence.center_lon
            }
        }
        self.alerts.append(alert)

        log_file = os.path.join(self.log_dir, f"geofence_alerts_{datetime.now().strftime('%Y%m%d')}.json")
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(self.alerts, f, indent=2, ensure_ascii=False)

        return alert
