"""
สคริปต์สำหรับแปลงโมเดล PyTorch (.pt) เป็น NCNN ความเร็วสูงสำหรับ Raspberry Pi
ใช้งาน: python export_ncnn_local.py [path_to_model.pt]
"""
import sys
import os

def main():
    model_path = sys.argv[1] if len(sys.argv) > 1 else 'best.pt'
    if not os.path.exists(model_path):
        for candidate in ['helmet_yolov8n.pt', 'yolov8n.pt']:
            if os.path.exists(candidate):
                model_path = candidate
                break

    if not os.path.exists(model_path):
        print(f"❌ ไม่พบไฟล์โมเดล {model_path} กรุณาระบุชื่อไฟล์โมเดล .pt ที่ต้องการแปลง")
        return

    print("=" * 60)
    print(f"🚀 เริ่มต้นแปลงโมเดล: {model_path} ➡️ NCNN (imgsz=320)")
    print("=" * 60)

    try:
        from ultralytics import YOLO
        model = YOLO(model_path)
        out_path = model.export(format='ncnn', imgsz=320)
        print("=" * 60)
        print(f"✅ แปลงโมเดลสำเร็จเรียบร้อย!")
        print(f"📍 โฟลเดอร์โมเดล NCNN: {out_path}")
        print("💡 นำโฟลเดอร์นี้ไปวางในโปรเจกต์บน Raspberry Pi เพื่อให้ระบบตรวจจับทำงานที่ FPS สูงสุดได้ทันที")
        print("=" * 60)
    except Exception as e:
        print(f"⚠️ เกิดข้อผิดพลาด: {e}")

if __name__ == '__main__':
    main()

