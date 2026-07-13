# Kindle Highlight Uploader

App Python (Tkinter) để đồng bộ highlight từ Kindle lên API của bạn.

## Cài đặt

```bash
pip install -r requirements.txt
```

## Cấu hình

Mở `config.json` và sửa lại:

```json
{
  "api_url": "https://your-api.example.com/api/highlights",
  "api_key": "YOUR_API_KEY_HERE",
  "auth_header": "Authorization",
  "auth_prefix": "Bearer "
}
```

- `api_url`: endpoint API nhận dữ liệu highlight (POST).
- `api_key`: API key của bạn (để trống hoặc giữ nguyên `YOUR_API_KEY_HERE` nếu API không cần auth).
- `auth_header` / `auth_prefix`: dùng cho trường hợp API cần header khác, ví dụ
  `X-API-Key` thay vì `Authorization: Bearer ...`.

## Chạy app

```bash
python kindle_highlight_uploader.py
```

## Cách dùng

1. Cắm Kindle vào máy tính qua cáp USB, chọn chế độ "Transfer files" nếu máy hỏi.
2. Mở app — app sẽ tự tìm file `documents/My Clippings.txt` trên ổ đĩa Kindle.
   - Nếu không tự tìm thấy, bấm **"Dò lại ổ Kindle"** hoặc **"Chọn file thủ công"**.
3. Bấm **"⬆️ Đồng bộ Highlight lên API"**.
4. Theo dõi log ngay trong app để biết kết quả (số lượng highlight, status code API, lỗi nếu có).

## Format dữ liệu gửi lên API

Mặc định, app gửi POST JSON dạng:

```json
{
  "source": "kindle",
  "synced_at": "2026-07-13T10:00:00",
  "count": 3,
  "highlights": [
    {
      "title": "Tên sách",
      "author": "Tác giả",
      "type": "Highlight",
      "location": "1234-1236",
      "page": null,
      "added_date": "Sunday, June 1, 2025 10:32:11 AM",
      "content": "Nội dung highlight..."
    }
  ]
}
```

Nếu API của bạn cần format khác (field khác, endpoint khác, cách xác thực khác...),
sửa trực tiếp hàm `upload_to_api()` trong file `kindle_highlight_uploader.py`.

## Lưu ý

- File Kindle thực sự lưu highlight tên là **`My Clippings.txt`** (nằm trong thư mục
  `documents/` ở gốc ổ đĩa Kindle) — không phải `function.txt`. Nếu bạn có ý khác về
  tên file, hãy cho mình biết để chỉnh lại code.
- App chỉ tìm ổ đĩa gắn ngoài qua USB (mass storage mode), không hỗ trợ Kindle qua Wi-Fi/Send-to-Kindle.
