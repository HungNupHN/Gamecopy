import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import re

class ReviewerGameTool:
    def __init__(self, root):
        self.root = root
        self.root.title("Reviewer Game Tool v2.0 - Steam & Riot")
        self.root.geometry("700x550")

        # Tạo Tab
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(pady=10, expand=True, fill="both")

        # --- TAB 1: STEAM ---
        self.tab_steam = tk.Frame(self.notebook)
        self.notebook.add(self.tab_steam, text="   STEAM   ")
        self.setup_steam_tab()

        # --- TAB 2: RIOT GAMES ---
        self.tab_riot = tk.Frame(self.notebook)
        self.notebook.add(self.tab_riot, text="   RIOT GAMES   ")
        self.setup_riot_tab()

        # Thanh trạng thái chung
        self.status_label = tk.Label(root, text="Sẵn sàng", fg="blue", relief=tk.SUNKEN, anchor="w")
        self.status_label.pack(side=tk.BOTTOM, fill="x")

    # ==========================================
    # LOGIC TAB 2: RIOT GAMES (THEO YÊU CẦU MỚI)
    # ==========================================
    def setup_riot_tab(self):
        frame = self.tab_riot
        
        # 1. Chọn Game Source
        tk.Label(frame, text="Bước 1: Chọn Folder chứa game (Trên ổ cứng rời)", font=("Arial", 10, "bold")).pack(pady=10)
        self.riot_src_path = tk.StringVar()
        f1 = tk.Frame(frame)
        f1.pack(fill="x", padx=20)
        tk.Entry(f1, textvariable=self.riot_src_path).pack(side="left", fill="x", expand=True)
        tk.Button(f1, text="Chọn Folder Game", command=self.select_riot_src).pack(side="left")
        
        # 2. Chọn Nơi Cài (Ổ C)
        tk.Label(frame, text="Bước 2: Chọn nơi muốn cài trên máy này (Thường là C:/)", font=("Arial", 10, "bold")).pack(pady=10)
        self.riot_dest_path = tk.StringVar(value="C:/") # Mặc định ổ C
        f2 = tk.Frame(frame)
        f2.pack(fill="x", padx=20)
        tk.Entry(f2, textvariable=self.riot_dest_path).pack(side="left", fill="x", expand=True)
        tk.Button(f2, text="Chọn Nơi Đến", command=self.select_riot_dest).pack(side="left")

        # 3. Loại Game
        tk.Label(frame, text="Xác nhận loại game đang chọn:", font=("Arial", 10)).pack(pady=5)
        self.riot_game_type = tk.StringVar(value="lol")
        tk.Radiobutton(frame, text="League of Legends", variable=self.riot_game_type, value="lol").pack()
        tk.Radiobutton(frame, text="VALORANT", variable=self.riot_game_type, value="val").pack()

        # 4. Nút chạy
        tk.Button(frame, text="🚀 COPY & CẤU HÌNH YAML", command=self.start_riot_process, 
                  bg="#D32F2F", fg="white", font=("Arial", 12, "bold")).pack(pady=20)
        
        tk.Label(frame, text="Lưu ý: Tool sẽ tự động sửa file .yaml trong ProgramData", fg="gray", font=("Arial", 8, "italic")).pack()

    def select_riot_src(self):
        path = filedialog.askdirectory(title="Chọn thư mục game (VD: League of Legends)")
        if path: 
            self.riot_src_path.set(path)
            # Tự động đoán game dựa trên tên folder
            if "League of Legends" in path: self.riot_game_type.set("lol")
            if "VALORANT" in path: self.riot_game_type.set("val")

    def select_riot_dest(self):
        path = filedialog.askdirectory(title="Chọn ổ đĩa đích (VD: C:/)")
        if path: self.riot_dest_path.set(path)

    def start_riot_process(self):
        src = self.riot_src_path.get()
        dest_root = self.riot_dest_path.get()
        gtype = self.riot_game_type.get()

        if not src or not dest_root:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng chọn đủ nguồn và đích!")
            return

        threading.Thread(target=self.run_riot_copy, args=(src, dest_root, gtype)).start()

    def run_riot_copy(self, src, dest_root, gtype):
        folder_name = os.path.basename(src) # VD: League of Legends
        dest_full = os.path.join(dest_root, folder_name)

        # 1. COPY GAME
        self.status_label.config(text=f"Đang copy {folder_name} sang {dest_root}...")
        try:
            if os.path.exists(dest_full):
                shutil.rmtree(dest_full) # Xóa cũ nếu có để chép mới cho sạch
            shutil.copytree(src, dest_full)
        except Exception as e:
            messagebox.showerror("Lỗi Copy", str(e))
            return

        # 2. XỬ LÝ YAML
        self.status_label.config(text="Đang cấu hình file YAML...")
        
        # Định nghĩa đường dẫn ProgramData
        program_data = os.environ.get('ProgramData') # Thường là C:\ProgramData
        riot_metadata = os.path.join(program_data, "Riot Games", "Metadata")
        
        # Thông tin cụ thể từng game
        if gtype == "lol":
            meta_folder = os.path.join(riot_metadata, "league_of_legends.live")
            yaml_file = "league_of_legends.live.product_settings.yaml"
            # LoL cài thẳng vào folder
            install_path_str = dest_full.replace("\\", "/")
        else: # VALORANT
            meta_folder = os.path.join(riot_metadata, "valorant.live")
            yaml_file = "valorant.live.product_settings.yaml"
            # Valorant trỏ vào thư mục live con
            install_path_str = os.path.join(dest_full, "live").replace("\\", "/")

        install_root_str = dest_root.replace("\\", "/")
        if not install_root_str.endswith("/"): install_root_str += "/"

        # Tạo thư mục Metadata nếu chưa có
        os.makedirs(meta_folder, exist_ok=True)
        full_yaml_path = os.path.join(meta_folder, yaml_file)

        # Mẫu YAML mặc định nếu file chưa tồn tại (Dựa trên mẫu bạn cung cấp)
        default_yaml_content = self.get_default_yaml(gtype, install_path_str, install_root_str)

        if not os.path.exists(full_yaml_path):
            # Ghi file mới
            with open(full_yaml_path, "w", encoding="utf-8") as f:
                f.write(default_yaml_content)
        else:
            # Sửa file cũ bằng Regex (An toàn hơn thay thế chuỗi thuần)
            with open(full_yaml_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Thay thế đường dẫn Install Path
            content = re.sub(r'product_install_full_path: ".*?"', f'product_install_full_path: "{install_path_str}"', content)
            # Thay thế đường dẫn Root
            content = re.sub(r'product_install_root: ".*?"', f'product_install_root: "{install_root_str}"', content)
            
            with open(full_yaml_path, "w", encoding="utf-8") as f:
                f.write(content)

        self.status_label.config(text="✅ Hoàn tất! Đã copy và patch YAML thành công.")
        messagebox.showinfo("Thành công", f"Đã cài xong {gtype.upper()}. Hãy mở Riot Client!")

    def get_default_yaml(self, gtype, full_path, root_path):
        # Mẫu YAML chuẩn bạn cung cấp để tạo mới nếu máy chưa có
        if gtype == "lol":
            return f"""auto_patching_enabled_by_player: false
dependencies:
    Direct X 9:
        hash: "64367ec1cf47a4ad1e6a2a302a3376f7e2541245eadf11c76298f3790ff7a34e"
        phase: "Succeeded"
        version: "1.0.0"
    vanguard: true
product_install_full_path: "{full_path}"
product_install_root: "{root_path}"
settings:
    create_shortcut: false
    create_uninstall_key: true
    locale: "en_US"
should_repair: false
"""
        else: # Valorant
            return f"""auto_patching_enabled_by_player: false
dependencies:
    vanguard: true
product_install_full_path: "{full_path}"
product_install_root: "{root_path}"
settings:
    create_uninstall_key: true
    locale: "en_US"
should_repair: false
"""

    # ==========================================
    # LOGIC TAB 1: STEAM (GIỮ NGUYÊN)
    # ==========================================
    def setup_steam_tab(self):
        frame = self.tab_steam
        self.steam_source = tk.StringVar()
        self.steam_dest = tk.StringVar()
        self.steam_games = []

        tk.Label(frame, text="Chọn SteamLibrary Nguồn:", font=("Arial", 9, "bold")).pack(pady=5)
        f1 = tk.Frame(frame)
        f1.pack(fill="x", padx=10)
        tk.Entry(f1, textvariable=self.steam_source).pack(side="left", fill="x", expand=True)
        tk.Button(f1, text="...", command=lambda: self.steam_source.set(filedialog.askdirectory())).pack(side="left")

        tk.Label(frame, text="Chọn Thư mục Steam Đích:", font=("Arial", 9, "bold")).pack(pady=5)
        f2 = tk.Frame(frame)
        f2.pack(fill="x", padx=10)
        tk.Entry(f2, textvariable=self.steam_dest).pack(side="left", fill="x", expand=True)
        tk.Button(f2, text="...", command=lambda: self.steam_dest.set(filedialog.askdirectory())).pack(side="left")

        tk.Button(frame, text="🔍 QUÉT GAME STEAM", command=self.scan_steam, bg="#4CAF50", fg="white").pack(pady=10)
        
        self.steam_listbox = tk.Listbox(frame, selectmode=tk.EXTENDED, height=10)
        self.steam_listbox.pack(fill="both", expand=True, padx=10)

        tk.Button(frame, text="BẮT ĐẦU COPY STEAM", command=self.run_steam_copy, bg="#2196F3", fg="white").pack(pady=10)

    def scan_steam(self):
        src = self.steam_source.get()
        if not src: return
        steamapps = os.path.join(src, "steamapps")
        self.steam_listbox.delete(0, tk.END)
        self.steam_games = []
        try:
            for f in os.listdir(steamapps):
                if f.endswith(".acf"):
                    path = os.path.join(steamapps, f)
                    with open(path, 'r', errors='ignore') as file:
                        c = file.read()
                        name = re.search(r'"name"\s+"(.*?)"', c)
                        installdir = re.search(r'"installdir"\s+"(.*?)"', c)
                        if name and installdir:
                             # Check if folder exists
                            common_path = os.path.join(steamapps, "common", installdir.group(1))
                            if os.path.exists(common_path):
                                self.steam_games.append({
                                    "name": name.group(1),
                                    "acf": f,
                                    "dir": installdir.group(1),
                                    "full_src": common_path
                                })
                                self.steam_listbox.insert(tk.END, name.group(1))
        except Exception as e: messagebox.showerror("Lỗi", str(e))

    def run_steam_copy(self):
        idxs = self.steam_listbox.curselection()
        if not idxs: return
        threading.Thread(target=self.steam_worker, args=(idxs,)).start()

    def steam_worker(self, idxs):
        dst_root = self.steam_dest.get()
        dst_common = os.path.join(dst_root, "steamapps", "common")
        os.makedirs(dst_common, exist_ok=True)
        
        for i in idxs:
            game = self.steam_games[i]
            self.status_label.config(text=f"Steam: Đang copy {game['name']}...")
            
            # Copy ACF
            shutil.copy2(os.path.join(self.steam_source.get(), "steamapps", game['acf']), 
                         os.path.join(dst_root, "steamapps", game['acf']))
            # Copy Data
            dst_game = os.path.join(dst_common, game['dir'])
            shutil.copytree(game['full_src'], dst_game, dirs_exist_ok=True)
        
        self.status_label.config(text="✅ Steam Copy Hoàn tất!")
        messagebox.showinfo("Done", "Xong Steam!")

if __name__ == "__main__":
    root = tk.Tk()
    app = ReviewerGameTool(root)
    root.mainloop()