<?php
/**
 * Server PHP cơ bản - nhận HTTP request và lưu dữ liệu ra file.
 * Dùng chung với app "Kindle Highlight Uploader" (hoặc bất kỳ client nào
 * gửi POST JSON / file) - đóng vai trò API nhận dữ liệu.
 *
 * CÁCH CHẠY:
 *   php -S 0.0.0.0:8099 server.php
 *
 * Sau đó gọi tới:
 *   http://<ip-máy-này>:8099/api/highlights   (POST)
 *
 * Dữ liệu nhận được sẽ được lưu vào thư mục ./data/
 */

// ----------------------------------------------------------------------
// 1. Cấu hình
// ----------------------------------------------------------------------
$SAVE_DIR   = __DIR__ . '/data';       // thư mục lưu file nhận được
$API_PATH   = '/api/highlights';       // endpoint chấp nhận request
$API_KEY    = '';                      // để trống = không kiểm tra auth.
                                        // Nếu muốn bật auth, đặt vd:
                                        // $API_KEY = 'my-secret-key';

if (!is_dir($SAVE_DIR)) {
    mkdir($SAVE_DIR, 0777, true);
}

// ----------------------------------------------------------------------
// 2. Header CORS cơ bản (cho phép gọi từ trình duyệt/app khác nếu cần)
// ----------------------------------------------------------------------
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization, X-API-Key');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(204);
    exit;
}

// ----------------------------------------------------------------------
// 3. Hàm tiện ích
// ----------------------------------------------------------------------
function json_response($data, int $status = 200): void
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
    exit;
}

function check_api_key(string $expected): void
{
    if ($expected === '') {
        return; // không bật auth
    }

    $received = '';
    if (!empty($_SERVER['HTTP_AUTHORIZATION'])) {
        $received = str_ireplace('Bearer ', '', $_SERVER['HTTP_AUTHORIZATION']);
    } elseif (!empty($_SERVER['HTTP_X_API_KEY'])) {
        $received = $_SERVER['HTTP_X_API_KEY'];
    }

    if (!hash_equals($expected, $received)) {
        json_response(['success' => false, 'error' => 'Unauthorized: sai hoặc thiếu API key'], 401);
    }
}

// ----------------------------------------------------------------------
// 4. Router đơn giản
// ----------------------------------------------------------------------
$requestPath = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
$method      = $_SERVER['REQUEST_METHOD'];

// Trang chủ / health-check
if ($requestPath === '/' && $method === 'GET') {
    json_response([
        'success' => true,
        'message' => 'PHP server đang chạy trên port 8099',
        'endpoint' => $API_PATH,
    ]);
}

// Endpoint nhận dữ liệu
if ($requestPath === $API_PATH && $method === 'POST') {
    check_api_key($API_KEY);

    $timestamp = date('Y-m-d_H-i-s');
    $savedInfo = [];

    // Trường hợp 1: có file upload (multipart/form-data, ví dụ field "file")
    if (!empty($_FILES)) {
        foreach ($_FILES as $fieldName => $file) {
            if ($file['error'] !== UPLOAD_ERR_OK) {
                continue;
            }
            $safeName = preg_replace('/[^A-Za-z0-9._-]/', '_', basename($file['name']));
            $destPath = "{$SAVE_DIR}/{$timestamp}_{$safeName}";

            if (move_uploaded_file($file['tmp_name'], $destPath)) {
                $savedInfo[] = $destPath;
            }
        }
    }

    // Trường hợp 2: body là JSON hoặc text thô (POST raw body)
    $rawBody = file_get_contents('php://input');
    if ($rawBody !== '' && empty($_FILES)) {
        $ext = 'json';
        json_decode($rawBody); // thử parse để biết có phải JSON hợp lệ không
        if (json_last_error() !== JSON_ERROR_NONE) {
            $ext = 'txt';
        }
        $destPath = "{$SAVE_DIR}/{$timestamp}_upload.{$ext}";
        file_put_contents($destPath, $rawBody);
        $savedInfo[] = $destPath;
    }

    if (empty($savedInfo)) {
        json_response(['success' => false, 'error' => 'Không có dữ liệu nào được gửi lên'], 400);
    }

    json_response([
        'success'    => true,
        'message'    => 'Đã lưu dữ liệu thành công',
        'saved_files' => array_map('basename', $savedInfo),
        'timestamp'  => $timestamp,
    ]);
}

// Không khớp route nào
json_response(['success' => false, 'error' => 'Not found'], 404);