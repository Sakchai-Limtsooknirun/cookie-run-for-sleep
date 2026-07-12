import pyautogui
import keyboard
import time
import os


def auto_crop_tool(file_name):
    print(f"\n=====================================")
    print(f"📸 เป้าหมายปัจจุบัน: [ {file_name} ]")
    print(f"=====================================")

    print("1. เอาเมาส์ไปชี้ที่ มุมซ้าย-บน ของปุ่ม/ข้อความ แล้วกดปุ่ม 'F3'")
    keyboard.wait('F3')
    x1, y1 = pyautogui.position()
    print(f"   📍 ล็อกเป้ามุมซ้ายบน: (X:{x1}, Y:{y1})")
    time.sleep(0.5)  # หน่วงเวลาป้องกันปุ่มลั่น

    print("2. เอาเมาส์ไปชี้ที่ มุมขวา-ล่าง ของปุ่ม/ข้อความ แล้วกดปุ่ม 'F4'")
    keyboard.wait('F4')
    x2, y2 = pyautogui.position()
    print(f"   📍 ล็อกเป้ามุมขวาล่าง: (X:{x2}, Y:{y2})")
    time.sleep(0.5)

    # คำนวณหาความกว้างและความสูงของกรอบสี่เหลี่ยม
    width = x2 - x1
    height = y2 - y1

    # ป้องกันการลากเมาส์ผิดทิศทาง (ต้องลากจากซ้ายบนลงขวาล่างเสมอ)
    if width <= 0 or height <= 0:
        print("❌ พิกัดผิดพลาด! มุมขวาล่างต้องอยู่ต่ำกว่าและไปทางขวากว่ามุมซ้ายบนเสมอ")
        print("ข้ามการแคปรูปนี้... กรุณารันสคริปต์ใหม่ทีหลัง")
        return

    print(f"   กำลังครอบตัดภาพขนาด {width}x{height} พิกเซล...")

    # สั่งให้แคปหน้าจอเฉพาะพื้นที่ (Region) ที่คำนวณไว้ แล้วเซฟไฟล์ทันที
    screenshot = pyautogui.screenshot(region=(x1, y1, width, height))
    screenshot.save(file_name)

    print(f"✅ บันทึกรูปภาพเสร็จสิ้น! เซฟไว้ที่: {os.path.abspath(file_name)}")
    time.sleep(1)


if __name__ == '__main__':
    print("=== ✂️ โปรแกรม Auto-Crop สร้างไฟล์รูปภาพสำหรับบอท ===")
    print("คำแนะนำ: เปิดหน้าต่างเกม LDPlayer รอไว้เลย แล้วทำตามขั้นตอนทีละรูป\n")

    # รายชื่อไฟล์ทั้งหมดที่บอทหลักต้องการ
    images_to_crop = [
        # 'txt_double_coin.png',
        # 'btn_chest_1200.png',
        # 'btn_multi.png',
        # 'btn_multi_buy.png',
        # 'btn_play_boost.png',
        # 'btn_relay.png',
        # 'btn_ok.png',
        # 'btn_open_all.png',
        # 'btn_confirm.png',
        # 'btn_confirm_blue.png',
        # 'btn_main_play.png',
        # 'btn_fast_start.png',
        'icon_box_x1.png',
        # 'btn_pause.png',
        # 'btn_quit.png',
    ]

    for img_name in images_to_crop:
        auto_crop_tool(img_name)

    print("\n🎉 สร้างไฟล์รูปภาพครบทุกปุ่มเรียบร้อยแล้ว! สามารถเปิดบอทหลักรันฟาร์มได้เลยครับ")