import requests
import sys
import os
import subprocess
import time
import tkinter as tk
from tkinter import messagebox, ttk

class AppGuard:
    def __init__(self, current_version, auth_url):
        self.current_version = current_version
        self.auth_url = auth_url
        self.user_data = None
        
        # --- BƯỚC 0: TỰ DỌN DẸP FILE RÁC SAU UPDATE ---
        # Nếu phiên bản mới khởi động và thấy xác cũ (.old), thì xóa nó đi
        self.cleanup_old_version()

    def cleanup_old_version(self):
        """Xóa file exe cũ sau khi update thành công"""
        old_exe = sys.executable + ".old"
        if os.path.exists(old_exe):
            try:
                os.remove(old_exe)
                print("Đã dọn dẹp phiên bản cũ.")
            except:
                pass # Nếu chưa xóa được thì thôi, để lần sau

    def check_network_and_login(self):
        try:
            # Thêm timestamp qua loa để tránh GitHub cache file json cũ
            response = requests.get(f"{self.auth_url}?t={int(time.time())}", timeout=5)
            if response.status_code == 200:
                self.user_data = response.json()
                return True
        except:
            messagebox.showerror("Lỗi Mạng", "Không thể kết nối Server kiểm tra bản quyền.")
            return False
        return False

    def validate_access(self):
        if not self.user_data: return False

        # 1. Check Kill Switch
        if self.user_data.get("global_status") != "active":
            messagebox.showerror("Thông báo", self.user_data.get("message", "App đang bảo trì."))
            sys.exit()

        # 2. Check Update (TỰ ĐỘNG)
        server_ver = str(self.user_data.get("latest_version", "1.0"))
        
        # So sánh version (đơn giản)
        if server_ver != self.current_version:
            msg = f"Phát hiện bản mới: v{server_ver}\nBạn có muốn cập nhật ngay không?"
            if messagebox.askyesno("Cập nhật phần mềm", msg):
                download_url = self.user_data.get("download_url")
                if download_url:
                    self.perform_seamless_update(download_url)
                    return False # Dừng app cũ để update
                else:
                    messagebox.showerror("Lỗi", "Không tìm thấy link tải!")

        # 3. Check Key (Giữ nguyên như cũ)
        return self.check_license_key()

    def check_license_key(self):
        # Để code ngắn gọn tôi viết tóm tắt logic check key ở đây
        key_file = "license.key"
        saved_key = ""
        if os.path.exists(key_file):
            with open(key_file, "r") as f: saved_key = f.read().strip()
        
        from tkinter import simpledialog
        while True:
            key = saved_key if saved_key else simpledialog.askstring("Login", "Nhập Key bản quyền:")
            if key is None: sys.exit()
            
            if key in self.user_data.get("valid_keys", []):
                with open(key_file, "w") as f: f.write(key)
                return True
            else:
                saved_key = ""
                messagebox.showerror("Sai Key", "Key không hợp lệ!")

    # =======================================================
    # LOGIC UPDATE MỚI (KHÔNG CẦN FILE .BAT)
    # =======================================================
    def perform_seamless_update(self, url):
        """Tải file mới -> Đổi tên file cũ -> Thay thế -> Restart"""
        
        # Tạo cửa sổ Loading tải file
        progress_win = tk.Tk()
        progress_win.title("Đang cập nhật...")
        progress_win.geometry("300x100")
        tk.Label(progress_win, text="Đang tải phiên bản mới, vui lòng đợi...").pack(pady=10)
        bar = ttk.Progressbar(progress_win, length=250, mode='determinate')
        bar.pack(pady=5)
        
        current_exe = sys.executable # Đường dẫn file exe đang chạy
        temp_exe = current_exe + ".new" # Tên file tải tạm

        try:
            # 1. Tải file về
            response = requests.get(url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024
            wrote = 0
            
            with open(temp_exe, 'wb') as f:
                for data in response.iter_content(block_size):
                    wrote += len(data)
                    f.write(data)
                    # Update thanh loading
                    if total_size > 0:
                        percent = (wrote / total_size) * 100
                        bar['value'] = percent
                        progress_win.update()

            progress_win.destroy() # Tải xong tắt bảng loading

            # 2. "Ve sầu thoát xác" (Magic Step)
            old_exe_name = current_exe + ".old"
            
            # Nếu có file .old cũ rích thì xóa đi trước
            if os.path.exists(old_exe_name):
                os.remove(old_exe_name)

            # Đổi tên file đang chạy thành .old (Windows cho phép làm điều này!)
            os.rename(current_exe, old_exe_name)

            # Đổi tên file vừa tải (.new) thành tên chính thức (.exe)
            os.rename(temp_exe, current_exe)

            # 3. Khởi động lại app mới
            messagebox.showinfo("Thành công", "Cập nhật xong! Ứng dụng sẽ tự khởi động lại.")
            
            # Lệnh khởi động lại file exe mới
            subprocess.Popen([current_exe] + sys.argv[1:])
            
            # Tắt app cũ ngay lập tức
            sys.exit()

        except Exception as e:
            messagebox.showerror("Lỗi Update", f"Có lỗi xảy ra: {e}")
            # Nếu lỗi, cố gắng hồi phục lại tên file cũ
            if os.path.exists(current_exe + ".old") and not os.path.exists(current_exe):
                os.rename(current_exe + ".old", current_exe)
            sys.exit()