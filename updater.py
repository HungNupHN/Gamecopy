import requests
import sys
import os
import subprocess
import tkinter as tk
from tkinter import messagebox, simpledialog

class AppGuard:
    def __init__(self, current_version, auth_url):
        self.current_version = current_version
        self.auth_url = auth_url
        self.user_data = None

    def check_network_and_login(self):
        """Bước 1: Kết nối Server lấy dữ liệu"""
        try:
            response = requests.get(self.auth_url, timeout=5)
            if response.status_code == 200:
                self.user_data = response.json()
                return True
        except Exception as e:
            messagebox.showerror("Lỗi Mạng", "Không thể kết nối đến máy chủ xác thực!\nVui lòng kiểm tra internet.")
            return False
        return False

    def validate_access(self):
        """Bước 2: Kiểm tra trạng thái Global và Login"""
        if not self.user_data: return False

        # 1. Check Kill Switch (Khóa app toàn cục)
        if self.user_data.get("global_status") != "active":
            msg = self.user_data.get("message", "Ứng dụng tạm ngừng hoạt động.")
            messagebox.showerror("Thông báo từ Admin", msg)
            sys.exit() # Thoát app ngay lập tức

        # 2. Check Update
        server_ver = self.user_data.get("latest_version", "1.0")
        if server_ver > self.current_version:
            ans = messagebox.askyesno("Cập nhật", f"Đã có phiên bản mới ({server_ver}).\nBạn có muốn cập nhật ngay không?")
            if ans:
                download_link = self.user_data.get("download_url")
                self.do_update(download_link)
                return False # Dừng việc mở app cũ

        # 3. Login Dialog (Nhập Key)
        # Lưu key vào file local để lần sau đỡ phải nhập lại
        saved_key = ""
        if os.path.exists("license.key"):
            with open("license.key", "r") as f: saved_key = f.read().strip()

        while True:
            # Nếu có key lưu sẵn thì check luôn, nếu sai thì hiện bảng nhập
            input_key = saved_key if saved_key else simpledialog.askstring("Đăng nhập", "Nhập Key bản quyền của bạn:", parent=None)
            
            if input_key is None: # Bấm Cancel
                sys.exit()

            if input_key in self.user_data.get("valid_keys", []):
                # Login thành công -> Lưu key lại
                with open("license.key", "w") as f: f.write(input_key)
                return True
            else:
                saved_key = "" # Xóa key cũ nếu sai
                messagebox.showerror("Thất bại", "Key không hợp lệ hoặc đã bị khóa!")
                # Lặp lại vòng while để bắt nhập lại

    def do_update(self, url):
        """Bước 3: Tự động tải và cài đặt (Tricky part)"""
        try:
            # 1. Tải file exe mới về tên tạm
            new_exe_name = "update_new.exe"
            response = requests.get(url, stream=True)
            with open(new_exe_name, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk: f.write(chunk)
            
            # 2. Tạo file Batch (.bat) để thực hiện tráo đổi
            # Vì file exe đang chạy không thể tự xóa chính nó
            current_exe = sys.executable
            batch_script = f"""
            @echo off
            timeout /t 2 /nobreak
            del "{current_exe}"
            ren "{new_exe_name}" "{os.path.basename(current_exe)}"
            start "" "{current_exe}"
            del "%~f0"
            """
            
            with open("updater.bat", "w") as f:
                f.write(batch_script)

            # 3. Chạy file bat và thoát app này
            subprocess.Popen("updater.bat", shell=True)
            sys.exit()

        except Exception as e:
            messagebox.showerror("Lỗi Update", f"Không thể cập nhật: {e}")