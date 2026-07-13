# Setup Hướng dẫn

## 1. Cài đặt Dependencies

```bash
cd web
composer install
```

## 2. Cấu hình Environment

```bash
cp .env.example .env
# Edit .env nếu cần thiết
```

## 3. Chạy Server

```bash
# Cách 1: Dùng Composer script
composer start

# Cách 2: Chạy trực tiếp
php -S 0.0.0.0:8099
```

## 4. Test API

```bash
# Health check
curl http://localhost:8099/

# Upload file
curl -X POST \
  -F "file=@/path/to/file.txt" \
  http://localhost:8099/api/highlights

# Send JSON
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"highlights": ["text1", "text2"]}' \
  http://localhost:8099/api/highlights

# Với API Key
curl -X POST \
  -H "X-API-Key: your-secret-key" \
  -F "file=@/path/to/file.txt" \
  http://localhost:8099/api/highlights
```

## Thư viện được dùng

- **altorouter/altorouter** - Routing đơn giản
- **vlucas/phpdotenv** - Load config từ .env
- **monolog/monolog** - Logging chuyên nghiệp
