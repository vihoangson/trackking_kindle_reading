#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kindle Highlight Uploader
--------------------------
App Tkinter đơn giản:
  1. Khi cắm Kindle qua USB, app sẽ cố gắng tự tìm file "My Clippings.txt"
     (đây là file Kindle dùng để lưu tất cả highlight/note/bookmark của bạn,
     nằm trong thư mục documents/ ở gốc ổ đĩa Kindle).
  2. Bấm nút "Đồng bộ Highlight" để:
       - Đọc và parse file My Clippings.txt thành danh sách highlight.
       - Gửi (POST) dữ liệu đó lên API của bạn (cấu hình trong config.json).

Chỉnh sửa config.json để đổi api_url / api_key cho phù hợp với API thật của bạn.
Nếu API của bạn yêu cầu format khác, sửa hàm `upload_to_api()` bên dưới.
"""

import os
import sys
import json
import glob
import string
import threading
import traceback
from datetime import datetime

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

try:
    import requests
except ImportError:
    requests = None  # sẽ báo lỗi rõ ràng khi bấm nút upload nếu chưa cài

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
CLIPPINGS_RELATIVE_PATH = os.path.join("documents", "My Clippings.txt")


# ---------------------------------------------------------------------------
# 1. Dò tìm ổ đĩa Kindle
# ---------------------------------------------------------------------------
def find_kindle_clippings_path():
    """
    Cố gắng tự động tìm file 'My Clippings.txt' trên ổ đĩa Kindle đang cắm.
    Trả về đường dẫn nếu tìm thấy, None nếu không.
    """
    candidates = []

    if sys.platform.startswith("win"):
        # Windows: quét các ổ đĩa từ A: đến Z:
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                candidates.append(drive)

    elif sys.platform == "darwin":
        # macOS: ổ USB thường mount ở /Volumes/<TênỔ>
        for vol in glob.glob("/Volumes/*"):
            candidates.append(vol)

    else:
        # Linux: thường mount ở /media/<user>/<TênỔ> hoặc /run/media/<user>/<TênỔ>
        for base in ("/media", "/run/media"):
            if os.path.isdir(base):
                for user_dir in glob.glob(os.path.join(base, "*")):
                    for vol in glob.glob(os.path.join(user_dir, "*")):
                        candidates.append(vol)

    # Ưu tiên ổ đĩa có tên chứa "Kindle"
    candidates.sort(key=lambda p: ("kindle" not in os.path.basename(p).lower(), p))

    for drive in candidates:
        path = os.path.join(drive, CLIPPINGS_RELATIVE_PATH)
        if os.path.isfile(path):
            return path

    return None


# ---------------------------------------------------------------------------
# 2. Parse "My Clippings.txt"
# ---------------------------------------------------------------------------
def parse_clippings(file_path):
    """
    Parse file My Clippings.txt thành list các dict:
        {
            "title": str,
            "author": str | None,
            "type": "Highlight" | "Note" | "Bookmark" | ...,
            "location": str | None,
            "page": str | None,
            "added_date": str | None,   # nguyên văn theo Kindle
            "content": str,
        }
    Định dạng chuẩn của Kindle, mỗi entry cách nhau bởi dòng "=========="
    """
    with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
        raw = f.read()

    blocks = [b.strip("\r\n") for b in raw.split("==========") if b.strip()]
    entries = []

    for block in blocks:
        lines = [ln for ln in block.split("\n")]
        lines = [ln.rstrip("\r") for ln in lines]
        # Loại bỏ dòng trống ở đầu/cuối nhưng giữ cấu trúc 3 phần: title / meta / content
        lines = [ln for ln in lines if ln.strip() != ""] if len(lines) < 3 else lines

        if len(lines) < 2:
            continue

        title_line = lines[0].strip()
        meta_line = lines[1].strip()
        content = "\n".join(lines[2:]).strip()

        # Tách title / author: thường có dạng "Tên sách (Tác giả)"
        title, author = title_line, None
        if title_line.endswith(")") and "(" in title_line:
            idx = title_line.rfind("(")
            possible_author = title_line[idx + 1:-1].strip()
            possible_title = title_line[:idx].strip()
            if possible_author:
                title, author = possible_title, possible_author

        # Parse dòng meta, ví dụ:
        # "- Your Highlight at location 1234-1236 | Added on Sunday, June 1, 2025 10:32:11 AM"
        # "- Your Note at location 1234 | Added on ..."
        # "- Your Bookmark at page 12 | Added on ..."
        entry_type = None
        location = None
        page = None
        added_date = None

        lowered = meta_line.lower()
        for t in ("Highlight", "Note", "Bookmark", "Article", "Clip"):
            if t.lower() in lowered:
                entry_type = t
                break

        if "|" in meta_line:
            left, right = meta_line.split("|", 1)
        else:
            left, right = meta_line, ""

        if "location" in left.lower():
            after = left.lower().split("location", 1)[1].strip()
            location = after.split(" ")[0].strip(" .-")
        if "page" in left.lower():
            after = left.lower().split("page", 1)[1].strip()
            page = after.split("|")[0].strip(" .-")

        if "added on" in right.lower():
            added_date = right.lower().split("added on", 1)[1].strip()
            # Lấy lại phần gốc (giữ hoa/thường) từ right dựa trên vị trí
            idx = right.lower().find("added on")
            added_date = right[idx + len("added on"):].strip()

        entries.append({
            "title": title,
            "author": author,
            "type": entry_type,
            "location": location,
            "page": page,
            "added_date": added_date,
            "content": content,
        })

    return entries


# ---------------------------------------------------------------------------
# 3. Upload lên API
# ---------------------------------------------------------------------------
def load_config():
    if not os.path.isfile(CONFIG_PATH):
        raise FileNotFoundError(f"Không tìm thấy file cấu hình: {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def upload_to_api(entries, config, log_fn=print):
    """
    Gửi danh sách highlight lên API.
    CHỈNH SỬA phần này cho khớp với API thật của bạn (payload, header, endpoint...).
    """
    if requests is None:
        raise RuntimeError(
            "Thư viện 'requests' chưa được cài. Chạy: pip install requests"
        )

    api_url = config.get("api_url")
    api_key = config.get("api_key")
    auth_header = config.get("auth_header", "Authorization")
    auth_prefix = config.get("auth_prefix", "Bearer ")

    if not api_url or "your-api.example.com" in api_url:
        raise ValueError(
            "Bạn chưa cấu hình api_url trong config.json. Hãy mở config.json và sửa lại."
        )

    headers = {"Content-Type": "application/json"}
    if api_key and api_key != "YOUR_API_KEY_HERE":
        headers[auth_header] = f"{auth_prefix}{api_key}"

    payload = {
        "source": "kindle",
        "synced_at": datetime.now().isoformat(),
        "count": len(entries),
        "highlights": entries,
    }

    log_fn(f"Đang gửi {len(entries)} highlight tới {api_url} ...")
    resp = requests.post(api_url, headers=headers, json=payload, timeout=30)
    log_fn(f"API trả về status code: {resp.status_code}")

    try:
        body_preview = json.dumps(resp.json(), ensure_ascii=False, indent=2)
    except Exception:
        body_preview = resp.text

    log_fn(f"Nội dung phản hồi:\n{body_preview[:2000]}")

    resp.raise_for_status()
    return resp


# ---------------------------------------------------------------------------
# 4. Giao diện Tkinter
# ---------------------------------------------------------------------------
class KindleUploaderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Kindle Highlight Uploader")
        self.geometry("640x480")
        self.resizable(True, True)

        self.clippings_path_var = tk.StringVar(value="Chưa tìm thấy Kindle...")
        self.entries = []

        self._build_ui()
        self._auto_detect()

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        top_frame = ttk.Frame(self)
        top_frame.pack(fill="x", **pad)

        ttk.Label(top_frame, text="File My Clippings.txt:").pack(side="left")
        ttk.Label(top_frame, textvariable=self.clippings_path_var, foreground="blue").pack(
            side="left", padx=6
        )

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", **pad)

        ttk.Button(btn_frame, text="🔄 Dò lại ổ Kindle", command=self._auto_detect).pack(
            side="left", padx=4
        )
        ttk.Button(btn_frame, text="📂 Chọn file thủ công", command=self._choose_file).pack(
            side="left", padx=4
        )
        self.upload_btn = ttk.Button(
            btn_frame, text="⬆️ Đồng bộ Highlight lên API", command=self._on_upload_clicked
        )
        self.upload_btn.pack(side="left", padx=4)

        self.log_box = scrolledtext.ScrolledText(self, wrap="word", height=20)
        self.log_box.pack(fill="both", expand=True, **pad)
        self.log_box.configure(state="disabled")

    def log(self, message):
        self.log_box.configure(state="normal")
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_box.insert("end", f"[{timestamp}] {message}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _auto_detect(self):
        path = find_kindle_clippings_path()
        if path:
            self.clippings_path_var.set(path)
            self.log(f"Đã tìm thấy Kindle: {path}")
        else:
            self.clippings_path_var.set("Không tìm thấy — hãy chọn file thủ công")
            self.log("Không tự tìm thấy ổ Kindle. Hãy cắm USB rồi bấm 'Dò lại ổ Kindle', "
                      "hoặc dùng nút 'Chọn file thủ công'.")

    def _choose_file(self):
        path = filedialog.askopenfilename(
            title="Chọn file My Clippings.txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if path:
            self.clippings_path_var.set(path)
            self.log(f"Đã chọn file thủ công: {path}")

    def _on_upload_clicked(self):
        path = self.clippings_path_var.get()
        if not path or not os.path.isfile(path):
            messagebox.showerror("Lỗi", "Chưa có file My Clippings.txt hợp lệ.")
            return

        self.upload_btn.configure(state="disabled")
        threading.Thread(target=self._do_sync, args=(path,), daemon=True).start()

    def _do_sync(self, path):
        try:
            self.log(f"Đang đọc file: {path}")
            entries = parse_clippings(path)
            self.log(f"Đã parse được {len(entries)} highlight/note/bookmark.")

            if not entries:
                self.log("Không có dữ liệu nào để gửi.")
                return

            config = load_config()
            upload_to_api(entries, config, log_fn=self.log)
            self.log("✅ Đồng bộ thành công!")
            messagebox.showinfo("Thành công", f"Đã đồng bộ {len(entries)} highlight lên API.")

        except Exception as e:
            self.log(f"❌ Lỗi: {e}")
            self.log(traceback.format_exc())
            messagebox.showerror("Lỗi", str(e))
        finally:
            self.upload_btn.configure(state="normal")


if __name__ == "__main__":
    app = KindleUploaderApp()
    app.mainloop()
