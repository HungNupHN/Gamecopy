import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import re

class CopyTool:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Copy & Patch Tool")
        self.root.geometry("700x600")

        # --- BIẾN TOÀN CỤC ---
        self.stop_event = threading.Event() # Để sau này có thể làm nút Hủy nếu muốn

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

        # --- KHU VỰC TIẾN TRÌNH (DÙNG CHUNG) ---
        self.progress_frame = tk.Frame(root, relief=tk.SUNKEN, bd=1)
        self.progress_frame.pack(side=tk.BOTTOM, fill="x", padx=10, pady=5)
        
        self.lbl_status = tk.Label(self.progress_frame, text="Sẵn sàng", anchor="w")
        self.lbl_status.pack(fill="x")

        self.progress_bar = ttk.Progressbar(self.progress_frame, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill="x", pady=2)

        self.lbl_percent = tk.Label(self.progress_frame, text="0%", anchor="e")
        self.lbl_percent.pack(side="right")

    # ==========================================
    # Tình năng copy
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
        """
        Hàm copy thay thế cho shutil.copytree để hiện progress bar
        total_size_scope: Tổng dung lượng của cả quá trình (nếu copy nhiều game)
        current_copied_scope: Dung lượng đã copy trước đó (để nối tiếp bar)
        """
        if total_size_scope is None:
            total_size_scope = self.get_folder_size(src)
        
        current_copied = current_copied_scope

        # Tạo folder đích
        os.makedirs(dst, exist_ok=True)

        for item in os.listdir(src):
            s = os.path.join(src, item)
            d = os.path.join(dst, item)
            
            if os.path.isdir(s):
                # Đệ quy (Gọi lại chính nó cho thư mục con)
                current_copied = self.copy_with_progress(s, d, total_size_scope, current_copied)
            else:
                # Copy File từng Chunk để update bar
                try:
                    filesize = os.path.getsize(s)
                    with open(s, 'rb') as fsrc, open(d, 'wb') as fdst:
                        while True:
                            buf = fsrc.read(1024*1024) # Đọc mỗi lần 1MB
                            if not buf:
                                break
                            fdst.write(buf)
                            current_copied += len(buf)
                            
                            # Update UI
                            percent = (current_copied / total_size_scope) * 100
                            self.progress_bar['value'] = percent
                            self.lbl_percent.config(text=f"{percent:.1f}%")
                            self.root.update_idletasks() # Quan trọng: Giúp GUI không bị đơ
                except Exception as e:
                    print(f"Lỗi copy file {s}: {e}")
        
        return current_copied

    # ==========================================
    # LOGIC RIOT (TAB 2)
    # ==========================================
    def setup_riot_tab(self):
        frame = self.tab_riot
        
        tk.Label(frame, text="Game Source:", font=("Arial", 10, "bold")).pack(pady=(10,0))
        self.riot_src_path = tk.StringVar()
        f1 = tk.Frame(frame); f1.pack(fill="x", padx=20)
        tk.Entry(f1, textvariable=self.riot_src_path).pack(side="left", fill="x", expand=True)
        tk.Button(f1, text="...", command=self.select_riot_src).pack(side="left")
        
        tk.Label(frame, text="Game Destination:", font=("Arial", 10, "bold")).pack(pady=(10,0))
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

        self.lbl_status.config(text="Đang tính toán dung lượng...")
        try:
            # 1. Xóa cũ nếu có
            if os.path.exists(dest_full):
                self.lbl_status.config(text=f"Đang xóa bản cũ: {folder_name}...")
                shutil.rmtree(dest_full)
            
            # 2. Copy với Loading Bar
            self.lbl_status.config(text=f"Đang copy {folder_name}...")
            total_size = self.get_folder_size(src)
            self.copy_with_progress(src, dest_full, total_size_scope=total_size)
            
            # 3. Patch YAML
            self.lbl_status.config(text="Đang cấu hình YAML...")
            self.patch_riot_yaml(dest_full, dest_root, gtype)
            
            self.lbl_status.config(text="✅ Hoàn tất Riot Games!")
            messagebox.showinfo("Thành công", f"Đã cài xong {folder_name}")

        except Exception as e:
            messagebox.showerror("Lỗi", str(e))
            self.lbl_status.config(text="Gặp lỗi!")

    def patch_riot_yaml(self, dest_full, dest_root, gtype):
        # Logic patch YAML (Giữ nguyên như version 2, chỉ gọi hàm)
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
        
        # Mẫu YAML (Rút gọn cho code ngắn, logic như cũ)
        default_yaml = self.get_default_yaml_content(gtype, install_path_str, install_root_str)

        if not os.path.exists(full_yaml_path):
            with open(full_yaml_path, "w", encoding="utf-8") as f: f.write(default_yaml)
        else:
            with open(full_yaml_path, "r", encoding="utf-8") as f: content = f.read()
            content = re.sub(r'product_install_full_path: ".*?"', f'product_install_full_path: "{install_path_str}"', content)
            content = re.sub(r'product_install_root: ".*?"', f'product_install_root: "{install_root_str}"', content)
            with open(full_yaml_path, "w", encoding="utf-8") as f: f.write(content)

    def get_default_yaml_content(self, gtype, full, root):
        # (Giữ nguyên string YAML ở version trước của bạn)
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
    # LOGIC STEAM (TAB 1) - TABLE VERSION
    # ==========================================
    def setup_steam_tab(self):
        frame = self.tab_steam
        self.steam_source = tk.StringVar()
        self.steam_dest = tk.StringVar()
        self.steam_games = []

        # Phần chọn đường dẫn (Giữ nguyên)
        tk.Label(frame, text="Steam Lib (D:/testSteam)", font=("Arial", 10, "bold")).pack(pady=5)
        self.steam_source = tk.StringVar(value="D:/test/Steam")
        f1 = tk.Frame(frame); f1.pack(fill="x", padx=10)
        tk.Entry(f1, textvariable=self.steam_source).pack(side="left", fill="x", expand=True)
        tk.Button(f1, text="...", command=lambda: self.steam_source.set(filedialog.askdirectory())).pack(side="left")

        tk.Label(frame, text="Nơi cần copy (C:/Program Files (x86)/Steam):", font=("Arial", 10, "bold")).pack(pady=5)
        self.steam_dest = tk.StringVar(value="C:/Program Files (x86)/Steam")
        f2 = tk.Frame(frame); f2.pack(fill="x", padx=10)
        tk.Entry(f2, textvariable=self.steam_dest).pack(side="left", fill="x", expand=True)
        tk.Button(f2, text="...", command=lambda: self.steam_dest.set(filedialog.askdirectory())).pack(side="left")

        tk.Button(frame, text="🔍 QUÉT GAME STEAM", command=self.scan_steam, bg="#4CAF50", fg="white").pack(pady=10)
        
        # --- THAY ĐỔI LỚN Ở ĐÂY: DÙNG TREEVIEW THAY LISTBOX ---
        tree_frame = tk.Frame(frame)
        tree_frame.pack(fill="both", expand=True, padx=10)

        columns = ("name", "size")
        self.steam_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="extended")
        
        # --- CẬP NHẬT: THÊM TÍNH NĂNG SORT KHI CLICK VÀO TIÊU ĐỀ ---
        # Khi click vào cột "name", gọi hàm sort với reverse=False (A->Z)
        self.steam_tree.heading("name", text="Tên Game", 
                                command=lambda: self.treeview_sort_column(self.steam_tree, "name", False))
        
        # Khi click vào cột "size", gọi hàm sort với reverse=True (Nặng -> Nhẹ trước cho dễ nhìn)
        self.steam_tree.heading("size", text="Dung Lượng", 
                                command=lambda: self.treeview_sort_column(self.steam_tree, "size", True))
        
        # Chỉnh kích thước cột
        self.steam_tree.column("name", width=400, anchor="w")
        self.steam_tree.column("size", width=100, anchor="center")

        # Thanh cuộn (Scrollbar)
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.steam_tree.yview)
        self.steam_tree.configure(yscrollcommand=scrollbar.set)
        
        self.steam_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        tk.Button(frame, text="🚀 BẮT ĐẦU COPY", command=self.run_steam_copy, bg="#2196F3", fg="white").pack(pady=10)

    def parse_acf(self, file_path):
        """Hàm phụ trợ: Đọc file .acf và trả về Dictionary thông tin"""
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
                    # Chuyển đổi Byte sang GB (Làm tròn 2 số thập phân)
                    size_gb = round(int(size_match.group(1)) / (1024**3), 2)
                
                return {
                    "name": name_match.group(1),
                    "appid": id_match.group(1),
                    "install_dir": dir_match.group(1),
                    "size_gb": size_gb
                }
        except Exception:
            return None
        return None
    
    def treeview_sort_column(self, tv, col, reverse):
        """Hàm sắp xếp dữ liệu trong bảng Treeview"""
        # Lấy tất cả dữ liệu trong cột đó: [(giá trị, id_dòng), ...]
        l = [(tv.set(k, col), k) for k in tv.get_children('')]
        
        # XỬ LÝ LOGIC SẮP XẾP
        try:
            # Nếu là cột 'size', chuyển sang số thực (float) để so sánh (VD: 9.5 < 10.0)
            if col == "size":
                l.sort(key=lambda t: float(t[0]), reverse=reverse)
            else:
                # Nếu là cột tên, so sánh theo bảng chữ cái (chuyển về chữ thường để a == A)
                l.sort(key=lambda t: t[0].lower(), reverse=reverse)
        except ValueError:
            # Phòng trường hợp lỗi dữ liệu, sort mặc định
            l.sort(reverse=reverse)

        # Di chuyển các dòng trong bảng theo thứ tự mới
        for index, (val, k) in enumerate(l):
            tv.move(k, '', index)

        # Cập nhật lại tiêu đề cột để lần click tiếp theo sẽ đảo ngược thứ tự (Asc <-> Desc)
        tv.heading(col, command=lambda: self.treeview_sort_column(tv, col, not reverse))

    def scan_steam(self):
        src = self.steam_source.get()
        if not src: 
            messagebox.showwarning("Thiếu thông tin", "Vui lòng chọn thư mục Steam nguồn!")
            return

        steamapps = os.path.join(src, "steamapps")
        if not os.path.exists(steamapps):
            messagebox.showerror("Lỗi", "Không tìm thấy thư mục 'steamapps'!")
            return

        # Xóa dữ liệu cũ trong bảng
        for item in self.steam_tree.get_children():
            self.steam_tree.delete(item)
            
        self.steam_games = [] # Reset list data

        try:
            files = [f for f in os.listdir(steamapps) if f.endswith(".acf")]
            
            # Biến đếm index để map dữ liệu
            index_counter = 0

            for file in files:
                full_acf_path = os.path.join(steamapps, file)
                info = self.parse_acf(full_acf_path) # Gọi hàm parse_acf cũ
                
                if info:
                    common_path = os.path.join(steamapps, "common", info['install_dir'])
                    if os.path.exists(common_path):
                        # Lưu dữ liệu vào list gốc
                        self.steam_games.append({
                            "name": info['name'],
                            "acf": file,
                            "dir": info['install_dir'],
                            "full_src": common_path,
                            "size": info['size_gb']
                        })
                        
                        # Đưa lên bảng Treeview (Chỉ hiện Tên và Size)
                        # iid=index_counter: Để sau này biết dòng nào ứng với game nào trong list
                        self.steam_tree.insert("", "end", iid=index_counter, values=(info['name'], info['size_gb']))
                        index_counter += 1
                        
        except Exception as e:
            messagebox.showerror("Lỗi Quét", str(e))

    def run_steam_copy(self):
        # Lấy danh sách các dòng đang được chọn trong bảng
        selected_items = self.steam_tree.selection()
        
        if not selected_items:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn ít nhất 1 game!")
            return

        # Convert từ ID của bảng sang index của list self.steam_games
        selected_indices = [int(item_id) for item_id in selected_items]
        
        # Gọi luồng xử lý copy (Code luồng giữ nguyên, chỉ cần truyền đúng index)
        threading.Thread(target=self.steam_worker, args=(selected_indices,)).start()

    def steam_worker(self, idxs):
        dst_root = self.steam_dest.get()
        dst_common = os.path.join(dst_root, "steamapps", "common")
        os.makedirs(dst_common, exist_ok=True)
        
        # 1. Tính tổng dung lượng tất cả game đã chọn để hiển thị 1 thanh Loading duy nhất
        self.lbl_status.config(text="Đang tính toán tổng dung lượng...")
        total_bytes = 0
        selected_games = [self.steam_games[i] for i in idxs]
        
        for game in selected_games:
            total_bytes += self.get_folder_size(game['full_src'])
        
        current_bytes = 0

        # 2. Bắt đầu copy
        for game in selected_games:
            self.lbl_status.config(text=f"Đang copy: {game['name']}...")
            
            # Copy ACF (Nhẹ, copy thường)
            shutil.copy2(os.path.join(self.steam_source.get(), "steamapps", game['acf']), 
                         os.path.join(dst_root, "steamapps", game['acf']))
            
            # Copy Data (Nặng, dùng hàm custom)
            dst_game = os.path.join(dst_common, game['dir'])
            
            # Truyền current_bytes vào để nó nối tiếp phần trăm
            current_bytes = self.copy_with_progress(game['full_src'], dst_game, total_bytes, current_bytes)

        self.lbl_status.config(text="✅ Steam Copy Hoàn tất!")
        self.progress_bar['value'] = 100
        self.lbl_percent.config(text="100%")
        messagebox.showinfo("Done", "Đã copy xong tất cả game Steam đã chọn!")

if __name__ == "__main__":
    root = tk.Tk()
    app = CopyTool(root)
    root.mainloop()