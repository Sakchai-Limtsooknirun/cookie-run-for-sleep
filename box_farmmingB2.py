import platform
import ctypes
import json
import os
import random
import win32api
import win32con
import cv2
import numpy as np
import pyautogui
import time
import keyboard

# ==========================================
# [สำคัญมาก] แก้ปัญหาพิกัดเมาส์เพี้ยนจาก DPI Scaling
# ==========================================
if platform.system() == "Windows":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

# ==========================================
# ระบบ Cache รูปภาพบน RAM และ Scale
# ==========================================
TEMPLATE_CACHE = {}
SMART_CACHE_FILE = "smart_cache.json"
SMART_CACHE = {}

def load_smart_cache():
    global SMART_CACHE
    if os.path.exists(SMART_CACHE_FILE):
        try:
            with open(SMART_CACHE_FILE, 'r', encoding='utf-8') as f:
                SMART_CACHE = json.load(f)
                print(f"📦 โหลดข้อมูล Scale & Location ล่าสุดสำเร็จ ({len(SMART_CACHE)} ปุ่ม)")
        except:
            SMART_CACHE = {}
    else:
        SMART_CACHE = {}

def save_smart_cache():
    with open(SMART_CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(SMART_CACHE, f, indent=4)

def get_template(image_path):
    if image_path not in TEMPLATE_CACHE:
        template = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if template is None:
            print(f"❌ หาไฟล์รูป {image_path} ไม่พบ!")
            return None
        TEMPLATE_CACHE[image_path] = template
    return TEMPLATE_CACHE[image_path]

# ==========================================
# ดวงตาอัจฉริยะ V4 (Location Cache + Auto Refresh)
# ==========================================
def locate_image_multiscale(image_path, confidence=0.8, min_scale=0.5, max_scale=1.5, steps=20):
    screen = pyautogui.screenshot()
    screen_gray = cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2GRAY)
    screen_h, screen_w = screen_gray.shape

    template = get_template(image_path)
    if template is None: return None
    tH, tW = template.shape[:2]

    use_roi = False
    offset_x, offset_y = 0, 0

    if image_path in SMART_CACHE:
        cache_data = SMART_CACHE[image_path]
        scales = [cache_data['scale']]
        pad = 50
        x1 = max(0, cache_data['x'] - pad)
        y1 = max(0, cache_data['y'] - pad)
        x2 = min(screen_w, cache_data['x'] + cache_data['w'] + pad)
        y2 = min(screen_h, cache_data['y'] + cache_data['h'] + pad)

        search_area = screen_gray[y1:y2, x1:x2]
        offset_x, offset_y = x1, y1
        use_roi = True
    else:
        scales = np.linspace(min_scale, max_scale, steps)
        search_area = screen_gray

    best_match = None

    for scale in scales:
        resized_template = cv2.resize(template, (int(tW * scale), int(tH * scale)))
        r_tH, r_tW = resized_template.shape[:2]

        if r_tH > search_area.shape[0] or r_tW > search_area.shape[1]:
            continue

        result = cv2.matchTemplate(search_area, resized_template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if best_match is None or max_val > best_match[0]:
            best_match = (max_val, max_loc, scale, r_tW, r_tH)

        if max_val >= (confidence + 0.02):
            break

    if best_match is not None and best_match[0] >= confidence:
        max_val, max_loc, final_scale, r_tW, r_tH = best_match
        final_x = offset_x + max_loc[0]
        final_y = offset_y + max_loc[1]

        SMART_CACHE[image_path] = {
            'scale': final_scale,
            'x': final_x,
            'y': final_y,
            'w': r_tW,
            'h': r_tH
        }
        save_smart_cache()

        center_x = final_x + (r_tW // 2)
        center_y = final_y + (r_tH // 2)
        return center_x, center_y

    if use_roi:
        del SMART_CACHE[image_path]
        return locate_image_multiscale(image_path, confidence, min_scale, max_scale, steps)

    return None

# ==========================================
# ระบบคลิกเมาส์
# ==========================================
def human_click(base_x, base_y, variance=5):
    target_x = int(base_x + random.randint(-variance, variance))
    target_y = int(base_y + random.randint(-variance, variance))
    win32api.SetCursorPos((target_x, target_y))
    time.sleep(random.uniform(0.02, 0.05))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, target_x, target_y, 0, 0)
    time.sleep(random.uniform(0.04, 0.10))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, target_x, target_y, 0, 0)
    print(f"   [-] Clicked at ({target_x}, {target_y})")

def fast_click(x, y, variance=3):
    target_x = int(x + random.randint(-variance, variance))
    target_y = int(y + random.randint(-variance, variance))
    win32api.SetCursorPos((target_x, target_y))
    time.sleep(0.01)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, target_x, target_y, 0, 0)
    time.sleep(0.02)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, target_x, target_y, 0, 0)
    print(f"   [⚡] Fast Clicked at ({target_x}, {target_y})")

def find_and_click(image_path, confidence=0.8, timeout=None, check_interval=0.5):
    start_time = time.time()
    while True:
        if keyboard.is_pressed('q'):
            print("\n🛑 หยุดทำงานฉุกเฉิน!")
            exit()
        location = locate_image_multiscale(image_path, confidence=confidence)
        if location is not None:
            print(f"   [👀] พบภาพ {image_path} แล้ว! กำลังคลิก...")
            human_click(location[0], location[1])
            return True
        if timeout is not None:
            if time.time() - start_time > timeout:
                return False
            time.sleep(check_interval)
        else:
            return False

def is_image_present(image_path, confidence=0.8):
    location = locate_image_multiscale(image_path, confidence=confidence)
    return location is not None

# ==========================================
# โหมด 1: ฟาร์มเหรียญ (ตัวเดิม)
# ==========================================
def run_coin_farm_bot():
    print("🚀 เริ่มระบบ ฟาร์มเหรียญ! (กด 'q' ค้างไว้เพื่อหยุด)")
    loop_count = 1
    while True:
        print(f"\n=============================")
        print(f"🔄 เริ่มเล่นรอบที่ {loop_count}")
        print(f"=============================")

        # --- PHASE 1: หา Double Coins ด้วย Multi-Buy ---
        print("[Phase 1] ตรวจสอบบัฟ Double Coins...")
        if not is_image_present('public/assets/txt_double_coin.png', confidence=0.8):
            if not is_image_present('public/assets/btn_chest_1200.png', confidence=0.8):
                find_and_click('public/assets/btn_main_play.png', confidence=0.8, timeout=10.0)

            print("-> เริ่มกระบวนการ Multi-Buy...")
            while not is_image_present('public/assets/btn_multi.png', confidence=0.8):
                if keyboard.is_pressed('q'): exit()
                if not is_image_present('public/assets/btn_chest_1200.png', confidence=0.8):
                    find_and_click('public/assets/btn_main_play.png', confidence=0.8, timeout=10.0)
                    break
                find_and_click('public/assets/btn_chest_1200.png', confidence=0.7, timeout=1.0)
                time.sleep(0.5)

            while not is_image_present('public/assets/btn_multi_buy.png', confidence=0.8):
                if keyboard.is_pressed('q'): exit()
                find_and_click('public/assets/btn_multi.png', confidence=0.8, timeout=1.0)
                time.sleep(0.5)

            find_and_click('public/assets/btn_multi_buy.png', confidence=0.8, timeout=3.0)
            time.sleep(1.0)

            while not is_image_present('public/assets/txt_double_coin.png', confidence=0.8):
                time.sleep(2.0)

            find_and_click('public/assets/btn_play_boost.png', confidence=0.8, timeout=3.0)
            time.sleep(1.0)

        print("🎉 พร้อมสำหรับ Double Coins แล้ว! เตรียมตัววิ่ง...")
        time.sleep(0.5)
        find_and_click('public/assets/btn_play_boost.png', confidence=0.8, timeout=5.0)

        # --- PHASE 2: รอวิ่งผลัด (Relay) หรือ จบเกม (OK) ---
        print("[Phase 2] ปล่อยคุกกี้วิ่ง... รอจังหวะกดวิ่งผลัด หรือ หน้า Result!")
        start_time = time.time()
        relay_used = False
        check_ok_counter = 0

        while True:
            if keyboard.is_pressed('q'):
                exit()

            loc_relay = locate_image_multiscale('public/assets/backup/btn_relay.png', confidence=0.70, steps=7)
            if loc_relay is not None:
                print("⚡ พบปุ่มวิ่งผลัด! รีบกดทันที...")
                fast_click(loc_relay[0], loc_relay[1])
                relay_used = True
                time.sleep(1.0)
                break

            check_ok_counter += 1
            if check_ok_counter >= 5:
                loc_ok = locate_image_multiscale('public/assets/btn_ok.png', confidence=0.8, steps=5)
                if loc_ok is not None:
                    print("💀 เจอหน้า Result แล้ว! ข้ามสเตป...")
                    break
                check_ok_counter = 0

            if time.time() - start_time > 300.0:
                break
            time.sleep(0.01)

        # --- PHASE 3: กดปุ่ม OK หน้า Result ---
        find_and_click('public/assets/btn_ok.png', confidence=0.8, timeout=300.0)
        time.sleep(1.5)

        # --- PHASE 4: เปิดกล่อง Mystery Box ---
        has_box = find_and_click('public/assets/btn_open_all.png', confidence=0.8, timeout=4.0)
        if has_box:
            time.sleep(1.0)
            find_and_click('public/assets/btn_confirm_blue.png', confidence=0.8, timeout=5.0)
            time.sleep(1.5)

        time.sleep(1.5)
        find_and_click('public/assets/btn_confirm.png', confidence=0.8, timeout=5.0)
        time.sleep(0.5)

        # --- PHASE 5: กลับหน้า Lobby ---
        find_and_click('public/assets/btn_main_play.png', confidence=0.8, timeout=10.0)
        time.sleep(2)
        loop_count += 1

# ==========================================
# โหมด 2: ฟาร์มกล่อง (Fast Start + ออกทันทีเมื่อได้กล่อง)
# ==========================================
def run_box_farm_bot():
    print("🚀 เริ่มระบบ ฟาร์มกล่อง! (กด 'q' ค้างไว้เพื่อหยุด)")
    loop_count = 1
    while True:
        print(f"\n=============================")
        print(f"📦 เริ่มฟาร์มกล่องรอบที่ {loop_count}")
        print(f"=============================")

        print("[Phase 0] ตรวจสอบเงื่อนไขพิเศษหน้าล็อบบี้...")
        
        # เช็คให้ชัวร์ก่อนว่าตอนนี้ยืนอยู่หน้าแรกจริงๆ (มองเห็นปุ่ม Play ใหญ่)
        if is_image_present('public/assets/m3_reach_max_objective_full.png', confidence=0.8):
            print("   -> 🎯 เก็บชิ้นส่วนครบแล้ว")
            break
        print("   -> 🎯 เก็บชิ้นส่วนยังไม่ครบ หรือ หารูปไม่เจอ")
            # # ใส่รูปที่คุณต้องการเช็คตรงนี้ (เช่น มีปุ่มรับของฟรีเด้งขึ้นมา)
            # if is_image_present('public/assets/your_special_image.png', confidence=0.8):
            #     print("   -> 🎯 เจอรูปพิเศษ! กำลังทำซัมติง...")
                
            #     # สั่งให้กดรูปนั้น
            #     find_and_click('public/assets/your_special_image.png', confidence=0.8, timeout=3.0)
            #     time.sleep(1.0)
                
            #     # (ถ้าต้องกดกากบาทปิด หรือกดปุ่ม Confirm ต่อ ก็เขียน find_and_click ต่อตรงนี้ได้เลย)
                
        # --- PHASE 1: เข้าเกม ---
        if is_image_present('public/assets/btn_main_play.png', confidence=0.8):
            find_and_click('public/assets/btn_main_play.png', confidence=0.8, timeout=5.0)
            time.sleep(1.0)

        print("[Phase 1] กด Play เพื่อเริ่มวิ่ง...")
        if(is_image_present('public/assets/btn_chest_1200.png', confidence=0.8)):
            find_and_click('public/assets/btn_play_boost.png', confidence=0.8, timeout=5.0)

        # --- PHASE 2: ในเกม (กด Fast Start และรอกล่อง) ---
        # print("[Phase 2] เริ่มวิ่ง กำลังหาปุ่ม Fast Start และรอกล่อง x1...")
        start_time = time.time()
        # fast_start_clicked = False
        got_box = False
        time.sleep(1.0)

        while True:
            if keyboard.is_pressed('q'):
                exit()
            
            # # 1. หาปุ่ม Fast Start (ใช้ steps=15 เพื่อหาระยะซูมให้เจอในรอบแรก)
            # if not fast_start_clicked:
            #     loc_fast = locate_image_multiscale('public/assets/btn_fast_start.png', confidence=0.8, steps=15)
            #     if loc_fast is not None:
            #         print("⚡ พบปุ่ม Fast Start! กดใช้งาน...")
            #         fast_click(loc_fast[0], loc_fast[1])
            #         fast_start_clicked = True

            # 2. หารูปกล่อง x1 (หน่วงเวลาให้กด Fast Start ก่อน หรือผ่านไป 2 วินาทีค่อยเริ่มหา จะได้ไม่แย่ง CPU)
            # if (time.time() - start_time > 2.0):
            #     # ใช้ steps=15 เพื่อหาขนาดกล่องให้เจอในรอบแรกเช่นกัน
            #     loc_box = locate_image_multiscale('public/assets/icon_box_x1.png', confidence=0.75, steps=15)
            #     if loc_box is not None:
            #         print("🎁 ได้รับกล่องแล้ว! เตรียมตัวกดออก...")
            #         got_box = True
            #         break

            # 3. เผื่อกรณีวิ่งจนตาย หรือไม่เจอกล่องแล้วเด้งหน้า OK
            loc_ok = is_image_present('public/assets/btn_ok.png', confidence=0.8)
            if loc_ok:
                print("💀 คุกกี้ตายก่อนได้กล่อง เจอหน้า Result แล้ว...")
                break

            # # 4. Timeout กันบั๊ก (วิ่งเกิน 2.5 นาทีข้ามไปเริ่มใหม่)
            # if time.time() - start_time > 150.0:
            #     print("⚠️ วิ่งนานเกินไป ข้ามรอบนี้")
            #     break

            time.sleep(0.05)

        # if got_box:
        #     print("[Phase 3] กำลังกดออกเกม...")
        #     # ⚠️ อัปเดต: ลด confidence ลงเหลือ 0.65 เพื่อให้บอทมองข้ามสีพื้นหลังที่เปลี่ยนไป
        #     find_and_click('public/assets/btn_pause.png', confidence=0.65, timeout=5.0)
        #     time.sleep(0.5)
        #
        #     # กดปุ่ม Quit
        #     find_and_click('public/assets/btn_quit.png', confidence=0.8, timeout=5.0)
        #     time.sleep(0.5)
        #
        #     # กดปุ่ม Quit (Confirm) - ใช้รูป btn_quit.png เหมือนกัน
        #     find_and_click('public/assets/btn_quit.png', confidence=0.8, timeout=5.0)
        #     time.sleep(1.5)

        # --- PHASE 4: หน้า Result และเปิดกล่อง ---
        print("[Phase 4] รอรับของรางวัล...")
        find_and_click('public/assets/btn_ok.png', confidence=0.8, timeout=15.0)
        time.sleep(1.5)

        # หากล่องและเปิด
        has_box = find_and_click('public/assets/btn_open_all.png', confidence=0.8, timeout=15)
        if has_box:
            time.sleep(1.0)
            time.sleep(1.5)
        else:
            print("-> ไม่ได้กล่อง หรือเผลอกดข้ามไป")
            find_and_click('public/assets/btn_confirm.png', confidence=0.8, timeout=15)

        # เช็คปุ่ม Confirm ทั่วไป
        while is_image_present('public/assets/btn_confirm.png', confidence=0.8):
            find_and_click('public/assets/btn_confirm.png', confidence=0.8, timeout=15)
            time.sleep(1)

        # --- PHASE 5: กลับหน้า Lobby ---
        find_and_click('public/assets/btn_main_play.png', confidence=0.8, timeout=10.0)
        time.sleep(2)

        loop_count += 1

if __name__ == '__main__':
    print("===================================")
    print("🎮 Visual Farm Bot Initialization 🎮")
    print("===================================")

    ans = input("❓ คุณได้เปลี่ยนขนาดหน้าต่าง LDPlayer จากรอบที่แล้วหรือไม่? (y/n): ").strip().lower()

    if ans == 'y':
        print("🗑️ ล้างข้อมูลเดิม... บอทจะทำการสแกนหาตำแหน่งและขนาดใหม่ทั้งหมดในรอบแรก")
        SMART_CACHE = {}
        save_smart_cache()
    else:
        load_smart_cache()

    time.sleep(1)

    # print("\nกรุณาเลือกโหมดการทำงาน:")
    # print("1: ฟาร์มเหรียญ (ซื้อ Double Coin + วิ่งผลัด)")
    # print("2: ฟาร์มกล่อง (กด Fast Start + ได้กล่องกดออกทันที)")
    # mode = input("👉 พิมพ์หมายเลขโหมด (1 หรือ 2): ").strip()
    #
    # if mode == '2':
    run_box_farm_bot()
    # else:
    #     run_coin_farm_bot()