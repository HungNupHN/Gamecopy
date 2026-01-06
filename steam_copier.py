import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import re

class SteamGameCopier:
    def __init__(self, root):
        self.root = root
        self.root.title("Reviewer Game Tool - Steam Auto Copy")
        self.root.geometry("600x500")

        # Biến lưu đường dẫn
        self.steam_source = tk.StringVar()
        self.steam_dest = tk.StringVar()
        self.steam_games = [] # Lưu danh sách game tìm được (Tên, ID, Đường dẫn)

        # --- GIAO DIỆN ---
        
        # 1. Chọn nguồn (Ổ cứng rời)
        tk.Label(root, text="Bước 1: Chọn thư mục gốc Steam nguồn (Ví dụ: E:\\SteamLibrary)", font=("Arial", 10, "bold")).pack(pady=5)
        frame_src = tk.Frame(root)
        frame_src.pack(fill="x", padx=10)
        tk.Entry(frame_src, textvariable=self.steam_source).pack(side="left", fill="x", expand=True)
        tk.Button(frame_src, text="Chọn Folder", command=self.select_source).pack(side="left")

        # 2. Chọn đích (Máy Review)
        tk.Label(root, text="Bước 2: Chọn thư mục gốc Steam đích (Ví dụ: C:\\Program Files (x86)\\Steam)", font=("Arial", 10, "bold")).pack(pady=5)
        frame_dest = tk.Frame(root)
        frame_dest.pack(fill="x", padx=10)
        tk.Entry(frame_dest, textvariable=self.steam_dest).pack(side="left", fill="x", expand=True)
        tk.Button(frame_dest, text="Chọn Folder", command=self.select_dest).pack(side="left")

        # Nút quét game
        tk.Button(root, text="🔍 QUÉT TÌM GAME", command=self.scan_games, bg="#4CAF50", fg="white").pack(pady=10)

        # 3. Danh sách game
        tk.Label(root, text="Danh sách game tìm thấy (Chọn game để copy):").pack()
        self.listbox = tk.Listbox(root, selectmode=tk.EXTENDED) # Cho phép chọn nhiều game
        self.listbox.pack(fill="both", expand=True, padx=10)

        # 4. Nút thực hiện
        tk.Button(root, text="🚀 BẮT ĐẦU COPY", command=self.start_copy_thread, bg="#2196F3", fg="white", font=("Arial", 12, "bold")).pack(pady=10)
        
        # Thanh trạng thái
        self.status_label = tk.Label(root, text="Sẵn sàng", fg="blue")
        self.status_label.pack(pady=5)

    def select_source(self):
        path = filedialog.askdirectory(title="Chọn thư mục chứa SteamLibrary trên ổ rời")
        if path: self.steam_source.set(path)

    def select_dest(self):
        path = filedialog.askdirectory(title="Chọn thư mục Steam trên máy Review")
        if path: self.steam_dest.set(path)

    def scan_games(self):
        """Hàm logic để đọc file .acf và tìm tên game"""
        src = self.steam_source.get()
        steamapps = os.path.join(src, "steamapps")
        
        if not os.path.exists(steamapps):
            messagebox.showerror("Lỗi", "Không tìm thấy thư mục 'steamapps'. Hãy chọn đúng thư mục gốc của Steam!")
            return

        self.listbox.delete(0, tk.END)
        self.steam_games = []

        # Quét tất cả file .acf
        try:
            for file in os.listdir(steamapps):
                if file.endswith(".acf"):
                    # Đọc file acf để lấy tên và ID
                    full_path = os.path.join(steamapps, file)
                    game_info = self.parse_acf(full_path)
                    
                    if game_info:
                        # Kiểm tra xem folder data game có tồn tại không
                        common_path = os.path.join(steamapps, "common", game_info['install_dir'])
                        if os.path.exists(common_path):
                            display_text = f"{game_info['name']} (ID: {game_info['appid']}) - {game_info['size_gb']} GB"
                            self.steam_games.append({
                                "name": game_info['name'],
                                "appid": game_info['appid'],
                                "folder_name": game_info['install_dir'],
                                "acf_file": file,
                                "common_path": common_path
                            })
                            self.listbox.insert(tk.END, display_text)
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi khi quét game: {e}")

    def parse_acf(self, file_path):
        """Đọc file ACF để lấy thông tin bằng Regex"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            name_match = re.search(r'"name"\s+"(.*?)"', content)
            id_match = re.search(r'"appid"\s+"(\d+)"', content)
            dir_match = re.search(r'"installdir"\s+"(.*?)"', content)
            size_match = re.search(r'"SizeOnDisk"\s+"(\d+)"', content) # Byte

            if name_match and id_match and dir_match:
                size_gb = 0
                if size_match:
                    size_gb = round(int(size_match.group(1)) / (1024**3), 2)
                
                return {
                    "name": name_match.group(1),
                    "appid": id_match.group(1),
                    "install_dir": dir_match.group(1),
                    "size_gb": size_gb
                }
        except:
            return None
        return None

    def start_copy_thread(self):
        """Chạy copy ở luồng riêng để không đơ ứng dụng"""
        selected_indices = self.listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Chưa chọn game", "Vui lòng chọn ít nhất 1 game để copy!")
            return
            
        threading.Thread(target=self.copy_process, args=(selected_indices,)).start()

    def copy_process(self, selected_indices):
        dest_root = self.steam_dest.get()
        dest_steamapps = os.path.join(dest_root, "steamapps")
        dest_common = os.path.join(dest_steamapps, "common")

        # Tạo thư mục nếu chưa có
        os.makedirs(dest_common, exist_ok=True)

        total = len(selected_indices)
        for i, idx in enumerate(selected_indices):
            game = self.steam_games[idx]
            self.status_label.config(text=f"Đang copy ({i+1}/{total}): {game['name']}...")
            
            # 1. Copy file .acf
            src_acf = os.path.join(self.steam_source.get(), "steamapps", game['acf_file'])
            dst_acf = os.path.join(dest_steamapps, game['acf_file'])
            try:
                shutil.copy2(src_acf, dst_acf)
            except Exception as e:
                print(f"Lỗi copy ACF: {e}")

            # 2. Copy thư mục Game (Nặng nhất)
            src_game = game['common_path']
            dst_game = os.path.join(dest_common, game['folder_name'])
            
            try:
                # dirs_exist_ok=True cho phép ghi đè/bổ sung nếu folder đã tồn tại
                shutil.copytree(src_game, dst_game, dirs_exist_ok=True)
            except Exception as e:
                print(f"Lỗi copy Data: {e}")

        self.status_label.config(text="✅ Hoàn tất! Hãy khởi động lại Steam.")
        messagebox.showinfo("Thành công", "Đã copy xong! Hãy tắt Steam hoàn toàn và mở lại để nhận game.")

# --- CHẠY APP ---
if __name__ == "__main__":
    root = tk.Tk()
    app = SteamGameCopier(root)
    root.mainloop()