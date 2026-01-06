import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import re
import sys

# QUAN TRỌNG: Import class từ file updater.py đang nằm cạnh bên
# PyInstaller sẽ nhìn thấy dòng này và tự động đóng gói file updater.py vào cùng.
from updater import AppGuard 

# --- CẤU HÌNH ---
AUTH_URL = "https://raw.githubusercontent.com/HungNupHN/Gamecopy/refs/heads/main/auth.json"
CURRENT_VERSION = "1.0"

class CopyTool:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Reviewer Game Tool v{CURRENT_VERSION}")
        self.root.geometry("700x600")

        # --- BIẾN TOÀN CỤC ---
        self.stop_event = threading.Event() 

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

        # --- TIẾN TRÌNH ---
        self.progress_frame = tk.Frame(root, relief=tk.SUNKEN, bd=1)
        self.progress_frame.pack(side=tk.BOTTOM, fill="x", padx=10, pady=5)
        
        self.lbl_status = tk.Label(self.progress_frame, text="Sẵn sàng", anchor="w")
        self.lbl_status.pack(fill="x")

        self.progress_bar = ttk.Progressbar(self.progress_frame, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill="x", pady=2)

        self.lbl_percent = tk.Label(self.progress_frame, text="0%", anchor="e")
        self.lbl_percent.pack(side="right")

    # ==========================================
    # CÁC HÀM HỖ TRỢ (CORE)
    # ==========================================
    def get_folder_size(self, path):
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
        return total_size

    def copy_with_progress(self, src, dst, total_size_scope=None, current_copied_scope=0):
        if total_size_scope is None:
            total_size_scope = self.get_folder_size(src)
        
        current_copied = current_copied_scope
        os.makedirs(dst, exist_ok=True)

        for item in os.listdir(src):
            s = os.path.join(src, item)
            d = os.path.join(dst, item)
            
            if os.path.isdir(s):
                current_copied = self.copy_with_progress(s, d, total_size_scope, current_copied)
            else:
                try:
                    with open(s, 'rb') as fsrc, open(d, 'wb') as fdst:
                        while True:
                            buf = fsrc.read(1024*1024)
                            if not buf: break
                            fdst.write(buf)
                            current_copied += len(buf)
                            
                            percent = (current_copied / total_size_scope) * 100
                            self.progress_bar['value'] = percent
                            self.lbl_percent.config(text=f"{percent:.1f}%")
                            self.root.update_idletasks()
                except Exception as e:
                    print(f"Lỗi copy file {s}: {e}")
        return current_copied

    # ==========================================
    # LOGIC RIOT
    # ==========================================
    def setup_riot_tab(self):
        frame = self.tab_riot
        tk.Label(frame, text="Game Source:", font=("Arial", 10, "bold")).pack(pady=(10,0))
        self.riot_src_path = tk.StringVar()
        f1 = tk.Frame(frame); f1.pack(fill="x", padx=20)
        tk.Entry(f1, textvariable=self.riot_src_path).pack(side="left", fill="x", expand=True)
        tk.Button(f1, text="...", command=self.select_riot_src).pack(side="left")
        
        tk.Label(frame, text="Game Destination (Thường là C:/):", font=("Arial", 10, "bold")).pack(pady=(10,0))
        self.riot_dest_path = tk.StringVar(value="C:/")
        f2 = tk.Frame(frame); f2.pack(fill="x", padx=20)
        tk.Entry(f2, textvariable=self.riot_dest_path).pack(side="left", fill="x", expand=True)
        tk.Button(f2, text="...", command=self.select_riot_dest).pack(side="left")

        tk.Label(frame, text="Loại Game:", font=("Arial", 10)).pack(pady=5)
        self.riot_game_type = tk.StringVar(value="lol")
        tk.Radiobutton(frame, text="League of Legends", variable=self.riot_game_type, value="lol").pack()
        tk.Radiobutton(frame, text="VALORANT", variable=self.riot_game_type, value="val").pack()

        tk.Button(frame, text="🚀 CHẠY (COPY + PATCH)", command=self.start_riot_process, 
                  bg="#D32F2F", fg="white", font=("Arial", 11, "bold")).pack(pady=20)

    def select_riot_src(self):
        path = filedialog.askdirectory()
        if path: 
            self.riot_src_path.set(path)
            if "League of Legends" in path: self.riot_game_type.set("lol")
            if "VALORANT" in path: self.riot_game_type.set("val")

    def select_riot_dest(self):
        path = filedialog.askdirectory()
        if path: self.riot_dest_path.set(path)

    def start_riot_process(self):
        src = self.riot_src_path.get()
        dest_root = self.riot_dest_path.get()
        if not src or not dest_root: return
        threading.Thread(target=self.run_riot_worker, args=(src, dest_root)).start()

    def run_riot_worker(self, src, dest_root):
        folder_name = os.path.basename(src)
        dest_full = os.path.join(dest_root, folder_name)
        gtype = self.riot_game_type.get()

        self.lbl_status.config(text="Đang tính toán...")
        try:
            if os.path.exists(dest_full):
                self.lbl_status.config(text=f"Xóa cũ: {folder_name}...")
                shutil.rmtree(dest_full)
            
            self.lbl_status.config(text=f"Copy {folder_name}...")
            total_size = self.get_folder_size(src)
            self.copy_with_progress(src, dest_full, total_size_scope=total_size)
            
            self.lbl_status.config(text="Cấu hình YAML...")
            self.patch_riot_yaml(dest_full, dest_root, gtype)
            
            self.lbl_status.config(text="✅ Hoàn tất!")
            messagebox.showinfo("Thành công", f"Đã cài xong {folder_name}")
        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

    def patch_riot_yaml(self, dest_full, dest_root, gtype):
        program_data = os.environ.get('ProgramData')
        riot_metadata = os.path.join(program_data, "Riot Games", "Metadata")
        
        if gtype == "lol":
            meta_folder = os.path.join(riot_metadata, "league_of_legends.live")
            yaml_file = "league_of_legends.live.product_settings.yaml"
            install_path_str = dest_full.replace("\\", "/")
        else: 
            meta_folder = os.path.join(riot_metadata, "valorant.live")
            yaml_file = "valorant.live.product_settings.yaml"
            install_path_str = os.path.join(dest_full, "live").replace("\\", "/")

        install_root_str = dest_root.replace("\\", "/")
        if not install_root_str.endswith("/"): install_root_str += "/"
        
        os.makedirs(meta_folder, exist_ok=True)
        full_yaml_path = os.path.join(meta_folder, yaml_file)
        
        default_yaml = self.get_default_yaml_content(gtype, install_path_str, install_root_str)

        if not os.path.exists(full_yaml_path):
            with open(full_yaml_path, "w", encoding="utf-8") as f: f.write(default_yaml)
        else:
            with open(full_yaml_path, "r", encoding="utf-8") as f: content = f.read()
            content = re.sub(r'product_install_full_path: ".*?"', f'product_install_full_path: "{install_path_str}"', content)
            content = re.sub(r'product_install_root: ".*?"', f'product_install_root: "{install_root_str}"', content)
            with open(full_yaml_path, "w", encoding="utf-8") as f: f.write(content)

    def get_default_yaml_content(self, gtype, full, root):
        if gtype == "lol":
            return f"""auto_patching_enabled_by_player: false
dependencies:
    Direct X 9:
        hash: "64367ec1cf47a4ad1e6a2a302a3376f7e2541245eadf11c76298f3790ff7a34e"
        phase: "Succeeded"
        version: "1.0.0"
    vanguard: true
product_install_full_path: "{full}"
product_install_root: "{root}"
settings:
    create_shortcut: false
    create_uninstall_key: true
    locale: "en_US"
should_repair: false"""
        else:
            return f"""auto_patching_enabled_by_player: false
dependencies:
    vanguard: true
product_install_full_path: "{full}"
product_install_root: "{root}"
settings:
    create_uninstall_key: true
    locale: "en_US"
should_repair: false"""

    # ==========================================
    # LOGIC STEAM
    # ==========================================
    def setup_steam_tab(self):
        frame = self.tab_steam
        
        tk.Label(frame, text="Steam Source:", font=("Arial", 10, "bold")).pack(pady=5)
        self.steam_source = tk.StringVar(value="D:/test/Steam")
        f1 = tk.Frame(frame); f1.pack(fill="x", padx=10)
        tk.Entry(f1, textvariable=self.steam_source).pack(side="left", fill="x", expand=True)
        tk.Button(f1, text="...", command=lambda: self.steam_source.set(filedialog.askdirectory())).pack(side="left")

        tk.Label(frame, text="Steam Dest:", font=("Arial", 10, "bold")).pack(pady=5)
        self.steam_dest = tk.StringVar(value="C:/Program Files (x86)/Steam")
        f2 = tk.Frame(frame); f2.pack(fill="x", padx=10)
        tk.Entry(f2, textvariable=self.steam_dest).pack(side="left", fill="x", expand=True)
        tk.Button(f2, text="...", command=lambda: self.steam_dest.set(filedialog.askdirectory())).pack(side="left")

        tk.Button(frame, text="🔍 QUÉT GAME STEAM", command=self.scan_steam, bg="#4CAF50", fg="white").pack(pady=10)
        
        # TREEVIEW
        tree_frame = tk.Frame(frame)
        tree_frame.pack(fill="both", expand=True, padx=10)

        columns = ("name", "size")
        self.steam_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="extended")
        
        self.steam_tree.heading("name", text="Tên Game", command=lambda: self.treeview_sort_column(self.steam_tree, "name", False))
        self.steam_tree.heading("size", text="Dung Lượng (GB)", command=lambda: self.treeview_sort_column(self.steam_tree, "size", True))
        
        self.steam_tree.column("name", width=400, anchor="w")
        self.steam_tree.column("size", width=100, anchor="center")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.steam_tree.yview)
        self.steam_tree.configure(yscrollcommand=scrollbar.set)
        
        self.steam_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        tk.Button(frame, text="🚀 BẮT ĐẦU COPY", command=self.run_steam_copy, bg="#2196F3", fg="white").pack(pady=10)

    def parse_acf(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            name_match = re.search(r'"name"\s+"(.*?)"', content)
            dir_match = re.search(r'"installdir"\s+"(.*?)"', content)
            size_match = re.search(r'"SizeOnDisk"\s+"(\d+)"', content)
            if name_match and dir_match:
                size_gb = 0
                if size_match: size_gb = round(int(size_match.group(1)) / (1024**3), 2)
                return { "name": name_match.group(1), "install_dir": dir_match.group(1), "size_gb": size_gb }
        except: return None
        return None
    
    def treeview_sort_column(self, tv, col, reverse):
        l = [(tv.set(k, col), k) for k in tv.get_children('')]
        try:
            if col == "size": l.sort(key=lambda t: float(t[0]), reverse=reverse)
            else: l.sort(key=lambda t: t[0].lower(), reverse=reverse)
        except ValueError: l.sort(reverse=reverse)
        for index, (val, k) in enumerate(l): tv.move(k, '', index)
        tv.heading(col, command=lambda: self.treeview_sort_column(tv, col, not reverse))

    def scan_steam(self):
        src = self.steam_source.get()
        if not src: return
        steamapps = os.path.join(src, "steamapps")
        if not os.path.exists(steamapps):
            messagebox.showerror("Lỗi", "Không tìm thấy thư mục 'steamapps'!")
            return

        for item in self.steam_tree.get_children(): self.steam_tree.delete(item)
        self.steam_games = [] 

        try:
            files = [f for f in os.listdir(steamapps) if f.endswith(".acf")]
            index_counter = 0
            for file in files:
                info = self.parse_acf(os.path.join(steamapps, file))
                if info:
                    common_path = os.path.join(steamapps, "common", info['install_dir'])
                    if os.path.exists(common_path):
                        self.steam_games.append({
                            "name": info['name'], "acf": file, "dir": info['install_dir'],
                            "full_src": common_path, "size": info['size_gb']
                        })
                        self.steam_tree.insert("", "end", iid=index_counter, values=(info['name'], info['size_gb']))
                        index_counter += 1
        except Exception as e: messagebox.showerror("Lỗi Quét", str(e))

    def run_steam_copy(self):
        selected_items = self.steam_tree.selection()
        if not selected_items: return
        selected_indices = [int(item_id) for item_id in selected_items]
        threading.Thread(target=self.steam_worker, args=(selected_indices,)).start()

    def steam_worker(self, idxs):
        dst_root = self.steam_dest.get()
        dst_common = os.path.join(dst_root, "steamapps", "common")
        os.makedirs(dst_common, exist_ok=True)
        
        self.lbl_status.config(text="Tính tổng dung lượng...")
        total_bytes = 0
        selected_games = [self.steam_games[i] for i in idxs]
        for game in selected_games: total_bytes += self.get_folder_size(game['full_src'])
        
        current_bytes = 0
        for game in selected_games:
            self.lbl_status.config(text=f"Đang copy: {game['name']}...")
            shutil.copy2(os.path.join(self.steam_source.get(), "steamapps", game['acf']), 
                         os.path.join(dst_root, "steamapps", game['acf']))
            
            dst_game = os.path.join(dst_common, game['dir'])
            current_bytes = self.copy_with_progress(game['full_src'], dst_game, total_bytes, current_bytes)

        self.lbl_status.config(text="✅ Steam Hoàn tất!")
        self.progress_bar['value'] = 100
        self.lbl_percent.config(text="100%")
        messagebox.showinfo("Done", "Xong!")

# ==========================================
# CHƯƠNG TRÌNH CHÍNH (MAIN)
# ==========================================
if __name__ == "__main__":
    # 1. Chạy AppGuard trước để kiểm tra Login/Update
    guard = AppGuard(CURRENT_VERSION, AUTH_URL)
    
    # Check mạng và Login
    if guard.check_network_and_login():
        # Check khóa app và version
        if guard.validate_access():
            # Nếu tất cả OK -> Mới bật giao diện chính lên
            root = tk.Tk()
            app = CopyTool(root)
            root.mainloop()
    else:
        # Nếu không có mạng hoặc không login được -> Thoát
        sys.exit()