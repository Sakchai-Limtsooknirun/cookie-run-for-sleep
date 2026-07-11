import time
import json
import random
import os
import win32api
import win32con
import keyboard

MACRO_FILE = "macro_record.json"


# ==========================================
# 1. ฟังก์ชันการคลิกแบบมนุษย์ (ยังคงความปลอดภัยไว้)
# ==========================================
def human_click(base_x, base_y, variance=5):
    """สุ่มพิกัดเล็กน้อยและหน่วงเวลาจังหวะกด เพื่อหลบ Anti-Cheat"""
    target_x = base_x + random.randint(-variance, variance)
    target_y = base_y + random.randint(-variance, variance)

    win32api.SetCursorPos((target_x, target_y))
    time.sleep(random.uniform(0.01, 0.03))

    # กดเมาส์ซ้ายลง
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, target_x, target_y, 0, 0)

    # สุ่มเวลาแช่นิ้วบนจอ
    hold_time = random.uniform(0.04, 0.10)
    time.sleep(hold_time)

    # ยกเมาส์ซ้ายขึ้น
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, target_x, target_y, 0, 0)
    print(f"   [-] Clicked at ({target_x}, {target_y})")


# ==========================================
# 2. โหมด Recording (กด S)
# ==========================================
def record_macro():
    print("\n[โหมด RECORD]")
    print(">> นำเมาส์ไปที่เกม แล้วกด 's' บนคีย์บอร์ดเพื่อเริ่มบันทึก...")
    keyboard.wait('s')
    time.sleep(0.5)  # ป้องกันการกดปุ่ม s ซ้ำซ้อน

    print("\n🔴 [RECORDING] กำลังบันทึก! (คลิกเมาส์ซ้ายเพื่อมาร์คจุด | กด 's' อีกครั้งเพื่อจบการบันทึก)")

    start_time = time.time()
    actions = []
    is_mouse_down = False

    while True:
        # ถ้ากด s อีกครั้ง ให้หยุดเรคคอร์ด
        if keyboard.is_pressed('s'):
            print("⏹️ [STOP] จบการบันทึก!")
            time.sleep(0.5)
            break

        # ดักจับการคลิกเมาส์ซ้าย (VK_LBUTTON = 0x01)
        state = win32api.GetAsyncKeyState(0x01)
        if state < 0:  # ตรวจจับว่าเมาส์ซ้ายถูกกด
            if not is_mouse_down:
                is_mouse_down = True
                x, y = win32api.GetCursorPos()
                time_offset = time.time() - start_time

                # บันทึกข้อมูลลง List
                actions.append({
                    "time_offset": time_offset,
                    "x": x,
                    "y": y
                })
                print(f"   [+] บันทึกคลิกที่เวลา {time_offset:.2f} วินาที -> (X:{x}, Y:{y})")
        else:
            is_mouse_down = False

        time.sleep(0.01)  # ป้องกัน CPU กินสเปค 100%

    # บันทึก List ลงไฟล์ JSON
    with open(MACRO_FILE, 'w', encoding='utf-8') as f:
        json.dump(actions, f, indent=4)
    print(f"💾 บันทึกข้อมูล {len(actions)} จุด ลงไฟล์ '{MACRO_FILE}' เรียบร้อยแล้ว!\n")


# ==========================================
# 3. โหมด Playback (กด D)
# ==========================================
def play_macro():
    if not os.path.exists(MACRO_FILE):
        print(f"\n❌ ไม่พบไฟล์ {MACRO_FILE} กรุณาเข้าโหมด Record (พิมพ์ 1) ก่อน!")
        return

    with open(MACRO_FILE, 'r', encoding='utf-8') as f:
        actions = json.load(f)

    if not actions:
        print("\n❌ ไฟล์ Record ว่างเปล่า ไม่มีพิกัดให้เล่น!")
        return

    print("\n[โหมด PLAYBACK]")
    try:
        cycles = int(input("🔄 ต้องการให้ทำซ้ำกี่ลูป (Cycle): "))
    except ValueError:
        print("❌ กรุณาใส่เป็นตัวเลขเท่านั้น!")
        return

    print(f"\n>> โหลดข้อมูล {len(actions)} จุดเสร็จสิ้น")
    print(">> สลับไปที่หน้าจอเกม แล้วกด 'd' บนคีย์บอร์ดเพื่อเริ่มรัน...")
    keyboard.wait('d')
    time.sleep(0.5)

    print("\n▶️ [PLAYING] บอทเริ่มทำงาน! (กด 'q' ค้างไว้เพื่อหยุดฉุกเฉิน)")

    for cycle in range(1, cycles + 1):
        print(f"\n--- 🔄 เริ่ม Cycle {cycle}/{cycles} ---")
        cycle_start_time = time.time()

        for action in actions:
            target_time = action["time_offset"]

            # รอจนกว่าจะถึงเวลาของแอคชันนั้นๆ (เทียบกับเวลาที่เริ่มรัน Cycle)
            while True:
                if keyboard.is_pressed('q'):
                    print("\n🛑 หยุดการทำงานฉุกเฉิน!")
                    return

                current_time_offset = time.time() - cycle_start_time
                if current_time_offset >= target_time:
                    break
                time.sleep(0.005)

            # เมื่อถึงเวลาที่บันทึกไว้ ให้สั่งคลิก (โดยส่งผ่านฟังก์ชัน human_click เพื่อหลบแบน)
            human_click(action["x"], action["y"])

    print("\n✅ ทำงานเสร็จสิ้นทุก Cycle แล้ว!")


# ==========================================
# เมนูหลัก (Main Menu)
# ==========================================
if __name__ == '__main__':
    while True:
        print("===================================")
        print("🎮 Cookie Run Macro Auto-Bot 🎮")
        print("===================================")
        print("1. 🔴 โหมด Record (กด 's' บันทึกจุด/เวลา)")
        print("2. ▶️ โหมด Playback (กด 'd' รันบอทตามลูป)")
        print("3. ❌ ออกจากโปรแกรม")

        choice = input("เลือกโหมด (1, 2 หรือ 3): ")

        if choice == '1':
            record_macro()
        elif choice == '2':
            play_macro()
        elif choice == '3':
            print("ลาก่อน!")
            break
        else:
            print("❌ เลือกไม่ถูกต้อง กรุณาลองใหม่\n")