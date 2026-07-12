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
# [OPTIMIZE 1] ระบบ Cache รูปภาพบน RAM
# โหลดรูปแค่ครั้งเดียว ช่วยลดภาระ Disk I/O ได้ 90%
# ==========================================
TEMPLATE_CACHE = {}
SMART_CACHE_FILE = "smart_cache.json" # เปลี่ยนชื่อไฟล์แคชใหม่ เพราะโครงสร้างข้อมูลเปลี่ยนไป
SMART_CACHE = {}
import platform
import ctypes

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

    # 1. ตรวจสอบว่ามีข้อมูล Location Cache หรือไม่
    use_roi = False
    offset_x, offset_y = 0, 0

    if image_path in SMART_CACHE:
        # ถ้าระบบจำได้ ให้ดึง Scale เดิมมาใช้
        cache_data = SMART_CACHE[image_path]
        scales = [cache_data['scale']]

        # ตีกรอบพิกัดเดิม (ROI) + บวกระยะปลอดภัย (Padding) 50 px รอบทิศ
        # ป้องกันกรณีปุ่มเกมมีอนิเมชันเด้งดึ๋ง หรือขยับนิดหน่อย
        pad = 50
        x1 = max(0, cache_data['x'] - pad)
        y1 = max(0, cache_data['y'] - pad)
        x2 = min(screen_w, cache_data['x'] + cache_data['w'] + pad)
        y2 = min(screen_h, cache_data['y'] + cache_data['h'] + pad)

        # ตัดภาพหน้าจอมาแค่กรอบเล็กๆ (เร็วขึ้น 90%)
        search_area = screen_gray[y1:y2, x1:x2]
        offset_x, offset_y = x1, y1
        use_roi = True
    else:
        # ถ้าไม่มีในแคช ให้สแกนหาใหม่หมดทั้งจอ
        scales = np.linspace(min_scale, max_scale, steps)
        search_area = screen_gray

    best_match = None

    # 2. เริ่มกระบวนการสแกน (ในกรอบ หรือ เต็มจอ)
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
            break  # เจอแบบมั่นใจแล้ว Early Stop ทันที

    # 3. ประเมินผลลัพธ์
    if best_match is not None and best_match[0] >= confidence:
        max_val, max_loc, final_scale, r_tW, r_tH = best_match

        # คำนวณพิกัดจริงบนหน้าจอคอม (เอาพิกัดในกรอบ + พิกัดออฟเซ็ต)
        final_x = offset_x + max_loc[0]
        final_y = offset_y + max_loc[1]

        # เซฟ/อัปเดต ข้อมูลลง Smart Cache
        SMART_CACHE[image_path] = {
            'scale': final_scale,
            'x': final_x,
            'y': final_y,
            'w': r_tW,
            'h': r_tH
        }
        save_smart_cache()

        # คำนวณจุดกึ่งกลางเพื่อให้เมาส์ไปคลิก
        center_x = final_x + (r_tW // 2)
        center_y = final_y + (r_tH // 2)
        return center_x, center_y

    # 4. ระบบฟื้นฟูอัตโนมัติ (Auto-Refresh Cache)
    # ถ้าหากวาดในกรอบ ROI เล็กๆ แล้วไม่เจอ แปลว่า "ผู้ใช้อาจจะย้ายหน้าต่างโปรแกรม!"
    if use_roi:
        # print(f"🔄 หน้าต่างอาจถูกย้าย! รีเฟรช Location ของ {image_path} ใหม่...")
        del SMART_CACHE[image_path]

        # เรียกตัวเองซ้ำอีก 1 รอบ (คราวนี้จะตกลงไปในเงื่อนไขการหาสแกนทั้งจอใหม่)
        return locate_image_multiscale(image_path, confidence, min_scale, max_scale, steps)

    return None

# ==========================================
# 1. ระบบคลิกแบบมนุษย์ (ป้องกันโดนแบน)
# ==========================================
def human_click(base_x, base_y, variance=5):
    target_x = int(base_x + random.randint(-variance, variance))
    target_y = int(base_y + random.randint(-variance, variance))

    win32api.SetCursorPos((target_x, target_y))
    time.sleep(random.uniform(0.02, 0.05))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, target_x, target_y, 0, 0)

    hold_time = random.uniform(0.04, 0.10)
    time.sleep(hold_time)

    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, target_x, target_y, 0, 0)
    print(f"   [-] Clicked at ({target_x}, {target_y})")


# ==========================================
# เขียน Wrapper ทับฟังก์ชันเก่า เพื่อให้โค้ดหลัก (Phase 1-5) ใช้งานได้เหมือนเดิม
# ==========================================
def find_and_click(image_path, confidence=0.8, timeout=None, check_interval=0.5):
    start_time = time.time()
    while True:
        if keyboard.is_pressed('q'):
            print("\n🛑 หยุดทำงานฉุกเฉิน!")
            exit()

        # เปลี่ยนมาใช้ Multi-scale แทน locateCenterOnScreen
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


def fast_click(x, y, variance=3):
    """ฟังก์ชันคลิกความเร็วสูง สำหรับปุ่มที่ต้องแข่งกับเวลา (วิ่งผลัด)"""
    target_x = int(x + random.randint(-variance, variance))
    target_y = int(y + random.randint(-variance, variance))

    win32api.SetCursorPos((target_x, target_y))
    time.sleep(0.01)  # หน่วงแค่นิดเดียวให้จอรับรู้
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, target_x, target_y, 0, 0)
    time.sleep(0.02)  # กดลงแล้วยกขึ้นทันที
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, target_x, target_y, 0, 0)
    print(f"   [⚡] Fast Clicked at ({target_x}, {target_y})")

# ==========================================
# 3. ลอจิกการทำงานหลัก (Main State Machine)
# ==========================================
def run_farm_bot():
    print("🚀 เริ่มระบบ Visual Farm Bot! (กด 'q' ค้างไว้เพื่อหยุด)")
    loop_count = 1

    while True:
        print(f"\n=============================")
        print(f"🔄 เริ่มเล่นรอบที่ {loop_count}")
        print(f"=============================")



        # --- PHASE 1: หา Double Coins ด้วย Multi-Buy ---
        print("[Phase 1] ตรวจสอบบัฟ Double Coins...")
        if not is_image_present('public/assets/txt_double_coin.png', confidence=0.8):
            print("  -> check ว่า อยู่หน้าแรกไหม ถ้าอยู่หน้าแรกให้กด play ก่อน")

            if not is_image_present('public/assets/btn_chest_1200.png', confidence=0.8):
                print("  -> ไม่เจอปุ่ม หีบ อาจจะอยู่หน้าแรก ---")
                find_and_click('public/assets/btn_main_play.png', confidence=0.8, timeout=10.0)

            print("-> ยังไม่มี Double Coins เริ่มกระบวนการ Multi-Buy...")

            # 1. วนลูปกดกล่อง 1200 จนกว่าปุ่ม Multi จะปรากฏ
            print("   -> ขั้นตอน 1: พยายามกดกล่อง 1200")
            while not is_image_present('public/assets/btn_multi.png', confidence=0.8):
                if keyboard.is_pressed('q'): exit()
                # ลด confidence ลงเหลือ 0.7 เผื่อกล่องมีเอฟเฟกต์เรืองแสง
                if not is_image_present('public/assets/btn_chest_1200.png', confidence=0.8):
                    find_and_click('public/assets/btn_main_play.png', confidence=0.8, timeout=10.0)
                    break

                find_and_click('public/assets/btn_chest_1200.png', confidence=0.7, timeout=1.0)
                time.sleep(0.5)

            # 2. วนลูปกดปุ่ม Multi จนกว่าหน้าต่าง Multi-Buy สีเขียวจะเด้งขึ้นมา
            print("   -> ขั้นตอน 2: พบปุ่ม Multi แล้ว กำลังกดเพื่อเปิดป๊อปอัป")
            while not is_image_present('public/assets/btn_multi_buy.png', confidence=0.8):
                if keyboard.is_pressed('q'): exit()
                find_and_click('public/assets/btn_multi.png', confidence=0.8, timeout=1.0)
                time.sleep(0.5)

            # 3. กดปุ่ม Multi-Buy สีเขียว
            print("   -> ขั้นตอน 3: กำลังกด Multi-Buy สีเขียว!")
            find_and_click('public/assets/btn_multi_buy.png', confidence=0.8, timeout=3.0)

            # 4. รอให้ระบบเกมสุ่มออโต้จนเสร็จ (ใช้เวลาประมาณ 2-3 วินาที)
            print("   -> รอระบบซื้อออโต้ทำงาน...")
            time.sleep(1.0)

            print("   -> เช็คว่าสุ่ม double coin ได้หรือยัง...")
            while not is_image_present('public/assets/txt_double_coin.png', confidence=0.8):
                print("   -> ยังสุ่ม double coin ไม่เสร็จ...")
                time.sleep(2.0)

            # 5. ปิดหน้าต่าง "Purchase complete!"
            print("   -> สุ่มสำเร็จ! กำลังปิดหน้าต่างป๊อปอัป")
            find_and_click('public/assets/btn_play_boost.png', confidence=0.8, timeout=3.0)
            time.sleep(1.0)

        print("🎉 พร้อมสำหรับ Double Coins แล้ว! เตรียมตัววิ่ง...")
        time.sleep(0.5)

        # สั่งกด Play เพื่อเริ่มเกมจริงๆ
        find_and_click('public/assets/btn_play_boost.png', confidence=0.8, timeout=5.0)

        # --- PHASE 2: รอวิ่งผลัด (Relay) หรือ จบเกม (OK) ---
        print("[Phase 2] ปล่อยคุกกี้วิ่ง... รอจังหวะกดวิ่งผลัด หรือ หน้า Result!")

        start_time = time.time()
        relay_used = False
        check_ok_counter = 0  # ตัวนับรอบเพื่อลดภาระ CPU

        while True:
            if keyboard.is_pressed('q'):
                print("\n🛑 หยุดทำงานฉุกเฉิน!")
                exit()

            # 1. สแกนหา "ปุ่มวิ่งผลัด" (ลด steps เหลือ 7 เพื่อให้ CPU คิดไวขึ้น)
            # ปรับ confidence เหลือ 0.75 เผื่อความคลาดเคลื่อนนิดหน่อยให้จับติดง่ายขึ้น
            loc_relay = locate_image_multiscale('public/assets/btn_relay.png', confidence=0.75, steps=7)
            if loc_relay is not None:
                print("⚡ พบปุ่มวิ่งผลัด! รีบกดทันที...")
                fast_click(loc_relay[0], loc_relay[1])  # ใช้ฟังก์ชันมือไว!
                relay_used = True
                time.sleep(1.0)  # หน่วงเวลาให้นินจาลงพื้นก่อน
                break

                # 2. เช็ค "ปุ่ม OK" แค่ 1 ครั้ง ต่อการเช็คปุ่มวิ่งผลัด 5 ครั้ง
            check_ok_counter += 1
            if check_ok_counter >= 5:
                loc_ok = locate_image_multiscale('public/assets/btn_ok.png', confidence=0.8, steps=5)
                if loc_ok is not None:
                    print("💀 คุกกี้ตายสนิท เจอหน้า Result แล้ว! ข้ามสเตป...")
                    break
                check_ok_counter = 0  # รีเซ็ตตัวนับ

            # เช็ค Timeout (5 นาที)
            if time.time() - start_time > 300.0:
                print("⚠️ รอนานเกินไป (Timeout) ข้ามไปสเตปถัดไป")
                break

            # ลดเวลาพักลูปเหลือ 0.01 (เพราะ OpenCV กินเวลาไปเยอะแล้ว)
            time.sleep(0.01)

        # --- PHASE 3: กดปุ่ม OK หน้า Result ---
        if relay_used:
            print("[Phase 3] รอคุกกี้ตัวที่สองวิ่งจนจบ... มองหาปุ่ม OK")
        else:
            print("[Phase 3] กำลังกดปุ่ม OK...")

        # ถ้าข้ามมาจาก Phase 2 เพราะเจอ OK แล้ว คำสั่งนี้จะค้นหาเจอและกดคลิกให้ทันทีในเสี้ยววินาทีครับ
        find_and_click('public/assets/btn_ok.png', confidence=0.8, timeout=300.0)
        time.sleep(1.5)

        # --- PHASE 4: เปิดกล่อง Mystery Box ---
        print("[Phase 4] ตรวจสอบกล่องรางวัล...")
        # ให้เวลามันหาปุ่ม Open all 4 วินาที เพราะบางรอบอาจจะไม่ได้กล่อง
        has_box = find_and_click('public/assets/btn_open_all.png', confidence=0.8, timeout=4.0)
        if has_box:
            time.sleep(1.0)
            find_and_click('public/assets/btn_confirm_blue.png', confidence=0.8, timeout=5.0)
            time.sleep(1.5)
        else:
            print("-> รอบนี้ไม่มีกล่อง ข้ามไป...")

        time.sleep(1.5)
        print("-> เช็คเผื่อมี level up จะได้กด confirm...")
        find_and_click('public/assets/btn_confirm.png', confidence=0.8, timeout=5.0)
        time.sleep(0.5)

        # --- PHASE 5: กลับหน้า Lobby ---
        print("[Phase 5] เตรียมเริ่มรอบใหม่...")
        find_and_click('public/assets/btn_main_play.png', confidence=0.8, timeout=10.0)
        time.sleep(2)  # รออนิเมชันกลับหน้าสุ่มไอเทม
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
        load_smart_cache()  # โหลด Smart Cache แทนอันเก่า

    time.sleep(1)
    run_farm_bot()