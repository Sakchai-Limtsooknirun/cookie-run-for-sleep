import random
import win32api
import win32con
import cv2
import numpy as np
import pyautogui
import time
import keyboard
import json
import os

# ==========================================
# [OPTIMIZE 1 & 2] ระบบ Cache รูปภาพบน RAM และ Cache Scale ลงไฟล์
# ==========================================
TEMPLATE_CACHE = {}
SCALE_CACHE_FILE = "scale_cache.json"
SCALE_CACHE = {}


def load_scale_cache():
    """โหลดประวัติการซูมหน้าจอจากไฟล์"""
    global SCALE_CACHE
    if os.path.exists(SCALE_CACHE_FILE):
        with open(SCALE_CACHE_FILE, 'r', encoding='utf-8') as f:
            SCALE_CACHE = json.load(f)
            print(f"📦 โหลดข้อมูล Scale หน้าจอเดิมสำเร็จ ({len(SCALE_CACHE)} รูป)")
    else:
        SCALE_CACHE = {}


def save_scale_cache():
    """เซฟประวัติการซูมหน้าจอลงไฟล์"""
    with open(SCALE_CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(SCALE_CACHE, f, indent=4)


def get_template(image_path):
    """โหลดรูปภาพจาก Cache ถ้าไม่มีค่อยไปโหลดจากไฟล์"""
    if image_path not in TEMPLATE_CACHE:
        template = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if template is None:
            print(f"❌ หาไฟล์รูป {image_path} ไม่พบ!")
            return None
        TEMPLATE_CACHE[image_path] = template
    return TEMPLATE_CACHE[image_path]


# ==========================================
# ดวงตาอัจฉริยะ (จำสเกลเพื่อเพิ่มความเร็ว)
# ==========================================
def locate_image_multiscale(image_path, confidence=0.8, min_scale=0.5, max_scale=1.5, steps=20):
    # 1. แคปหน้าจอ
    screen = pyautogui.screenshot()
    screen_gray = cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2GRAY)

    # 2. โหลดรูปเป้าหมาย
    template = get_template(image_path)
    if template is None: return None

    tH, tW = template.shape[:2]
    best_match = None

    # 3. ตรวจสอบว่ามี Scale ที่เคยหาเจอแล้วหรือไม่
    if image_path in SCALE_CACHE:
        # ถ้ามี ให้สแกนแค่ 1 สเกล (ไวขึ้น 20 เท่า)
        scales = [SCALE_CACHE[image_path]]
    else:
        # ถ้าไม่มี ให้สแกนกวาดหาใหม่ทั้งหมด
        scales = np.linspace(min_scale, max_scale, steps)

    for scale in scales:
        resized_template = cv2.resize(template, (int(tW * scale), int(tH * scale)))
        r_tH, r_tW = resized_template.shape[:2]

        if r_tH > screen_gray.shape[0] or r_tW > screen_gray.shape[1]:
            continue

        result = cv2.matchTemplate(screen_gray, resized_template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        # เก็บค่าที่ดีที่สุดเอาไว้ก่อน พร้อมจำค่า scale นั้นด้วย
        if best_match is None or max_val > best_match[0]:
            best_match = (max_val, max_loc, scale, r_tW, r_tH)

        # EARLY STOPPING
        if max_val >= (confidence + 0.02):
            # จำค่า Scale นี้ไว้ใช้คราวหน้า แล้วเซฟลงไฟล์
            if image_path not in SCALE_CACHE:
                SCALE_CACHE[image_path] = scale
                save_scale_cache()

            center_x = max_loc[0] + (r_tW // 2)
            center_y = max_loc[1] + (r_tH // 2)
            return center_x, center_y

    # 4. ถ้าหาจนครบสเกลแล้ว เอาอันที่พอผ่านเกณฑ์ที่ดีที่สุด
    if best_match is not None and best_match[0] >= confidence:
        max_val, max_loc, best_scale, r_tW, r_tH = best_match

        # จำค่า Scale นี้ไว้ใช้คราวหน้า แล้วเซฟลงไฟล์
        if image_path not in SCALE_CACHE:
            SCALE_CACHE[image_path] = best_scale
            save_scale_cache()

        center_x = max_loc[0] + (r_tW // 2)
        center_y = max_loc[1] + (r_tH // 2)
        return center_x, center_y

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
    time.sleep(0.01)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, target_x, target_y, 0, 0)
    time.sleep(0.02)
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

            print("   -> ขั้นตอน 1: พยายามกดกล่อง 1200")
            while not is_image_present('public/assets/btn_multi.png', confidence=0.8):
                if keyboard.is_pressed('q'): exit()
                if not is_image_present('public/assets/btn_chest_1200.png', confidence=0.8):
                    find_and_click('public/assets/btn_main_play.png', confidence=0.8, timeout=10.0)
                    break

                find_and_click('public/assets/btn_chest_1200.png', confidence=0.7, timeout=1.0)
                time.sleep(0.5)

            print("   -> ขั้นตอน 2: พบปุ่ม Multi แล้ว กำลังกดเพื่อเปิดป๊อปอัป")
            while not is_image_present('public/assets/btn_multi_buy.png', confidence=0.8):
                if keyboard.is_pressed('q'): exit()
                find_and_click('public/assets/btn_multi.png', confidence=0.8, timeout=1.0)
                time.sleep(0.5)

            print("   -> ขั้นตอน 3: กำลังกด Multi-Buy สีเขียว!")
            find_and_click('public/assets/btn_multi_buy.png', confidence=0.8, timeout=3.0)

            print("   -> รอระบบซื้อออโต้ทำงาน...")
            time.sleep(1.0)

            print("   -> เช็คว่าสุ่ม double coin ได้หรือยัง...")
            while not is_image_present('public/assets/txt_double_coin.png', confidence=0.8):
                print("   -> ยังสุ่ม double coin ไม่เสร็จ...")
                time.sleep(2.0)

            print("   -> สุ่มสำเร็จ! กำลังปิดหน้าต่างป๊อปอัป")
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
                print("\n🛑 หยุดทำงานฉุกเฉิน!")
                exit()

            # ปรับ steps ให้เยอะหน่อยในกรณีที่ต้องหาใหม่ แต่ถ้ามี cache แล้วมันจะใช้ 1 step เอง
            loc_relay = locate_image_multiscale('public/assets/btn_relay.png', confidence=0.75, steps=7)
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
                    print("💀 คุกกี้ตายสนิท เจอหน้า Result แล้ว! ข้ามสเตป...")
                    break
                check_ok_counter = 0

            if time.time() - start_time > 300.0:
                print("⚠️ รอนานเกินไป (Timeout) ข้ามไปสเตปถัดไป")
                break

            time.sleep(0.01)

        # --- PHASE 3: กดปุ่ม OK หน้า Result ---
        if relay_used:
            print("[Phase 3] รอคุกกี้ตัวที่สองวิ่งจนจบ... มองหาปุ่ม OK")
        else:
            print("[Phase 3] กำลังกดปุ่ม OK...")

        find_and_click('public/assets/btn_ok.png', confidence=0.8, timeout=300.0)
        time.sleep(1.5)

        # --- PHASE 4: เปิดกล่อง Mystery Box ---
        print("[Phase 4] ตรวจสอบกล่องรางวัล...")
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
        time.sleep(2)
        loop_count += 1


if __name__ == '__main__':
    print("===================================")
    print("🎮 Visual Farm Bot Initialization 🎮")
    print("===================================")

    # ดักถาม User ก่อนเริ่มทำงาน
    ans = input("❓ คุณได้เปลี่ยนขนาดหน้าต่าง LDPlayer จากรอบที่แล้วหรือไม่? (y/n): ").strip().lower()

    if ans == 'y':
        print("🗑️ ล้างข้อมูล Scale เดิม... บอทจะทำการสแกนหาขนาดใหม่ทั้งหมดในรอบแรก")
        SCALE_CACHE = {}
        save_scale_cache()  # เคลียร์ไฟล์
    else:
        load_scale_cache()  # โหลดข้อมูลเดิมมาใช้

    time.sleep(1)
    run_farm_bot()