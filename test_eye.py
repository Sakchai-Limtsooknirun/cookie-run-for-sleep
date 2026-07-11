import win32gui
import mss
import mss.tools
import ctypes

# [แก้ปัญหา DPI Scaling] สั่งให้ Windows รู้ว่าสคริปต์นี้จัดการ DPI เอง (สำคัญมาก!)
ctypes.windll.user32.SetProcessDPIAware()


def test_find_window(window_title="LDPlayer"):
    print(f"🔍 กำลังค้นหาหน้าต่างที่มีคำว่า '{window_title}'...")
    found_windows = []

    def enum_cb(hwnd, result):
        text = win32gui.GetWindowText(hwnd)
        # กรองเอาเฉพาะหน้าต่างที่ "มองเห็นได้จริง" และชื่อตรง
        if win32gui.IsWindowVisible(hwnd) and window_title.lower() in text.lower():
            rect = win32gui.GetWindowRect(hwnd)
            width = rect[2] - rect[0]
            height = rect[3] - rect[1]
            # ตัดหน้าต่างบั๊กที่มีขนาด 0x0 ทิ้งไป
            if width > 0 and height > 0:
                result.append((hwnd, text, rect))

    win32gui.EnumWindows(enum_cb, found_windows)

    if not found_windows:
        print("❌ ไม่พบหน้าต่างใดๆ เลย! (ลองเช็คชื่อหน้าต่างอีกครั้ง)")
        return

    print(f"✅ พบหน้าต่างที่เข้าข่าย {len(found_windows)} อัน ได้แก่:")
    for i, (h, t, r) in enumerate(found_windows):
        print(f"   [{i}] ชื่อ: '{t}' | พิกัด: {r}")

    # เลือกหน้าต่างอันแรกที่เจอมาทดสอบแคปภาพ
    target_hwnd, target_text, rect = found_windows[0]

    # ถ้าเล่นแบบ Full HD พิกัดขอบบนมักจะติด Title Bar
    monitor = {
        "left": rect[0],
        "top": rect[1],
        "width": rect[2] - rect[0],
        "height": rect[3] - rect[1]
    }

    print(f"\n📸 กำลังทดสอบใช้ mss แคปภาพหน้าต่าง: '{target_text}'")
    try:
        with mss.mss() as sct:
            # สั่งแคปภาพ
            sct_img = sct.grab(monitor)
            # เซฟไฟล์ออกมาดู
            output_file = "test_capture.png"
            mss.tools.to_png(sct_img.rgb, sct_img.size, output=output_file)
            print(f"🎉 สำเร็จ! เซฟรูปภาพหน้าต่างไว้ที่ '{output_file}' แล้ว")
            print("👉 กรุณาเปิดไฟล์รูปนี้ดูว่า แคปมาตรงกับหน้าจอเกมเป๊ะๆ ไหม?")
    except Exception as e:
        print(f"💥 เกิดข้อผิดพลาดตอนแคปจอ: {e}")


if __name__ == '__main__':
    # หากหน้าต่างคุณชื่อแปลกๆ ให้เปลี่ยนข้อความในวงเล็บได้เลย เช่น "LDPlayer-1"
    test_find_window("LDPlayer")