<?php
/**
 * Server PHP refactored với Composer libraries
 * Dùng: AltoRouter, phpdotenv, Monolog
 */

require_once __DIR__ . '/vendor/autoload.php';

use AltoRouter\Router;
use Dotenv\Dotenv;
use Monolog\Logger;
use Monolog\Handlers\StreamHandler;

// ==================== CONFIG ====================
$baseDir = dirname(__DIR__);
$dataDir = $baseDir . '/data';

// Tạo thư mục data nếu chưa có
if (!is_dir($dataDir)) {
    mkdir($dataDir, 0777, true);
}

// Load .env (nếu có)
if (file_exists($baseDir . '/.env')) {
    $dotenv = Dotenv::createImmutable($baseDir);
    $dotenv->load();
}

// Setup Logging
$logger = new Logger('api');
$logger->pushHandler(new StreamHandler('php://stdout'));

// Config
$apiKey = $_ENV['API_KEY'] ?? '';
$apiPath = $_ENV['API_PATH'] ?? '/api/highlights';

// ==================== CORS HEADERS ====================
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization, X-API-Key');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(204);
    exit;
}

// ==================== HELPER FUNCTIONS ====================
function json_response($data, int $status = 200): never
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
    exit;
}

function check_api_key(string $expected, Logger $logger): void
{
    if ($expected === '') {
        return;
    }

    $received = '';
    if (!empty($_SERVER['HTTP_AUTHORIZATION'])) {
        $received = str_ireplace('Bearer ', '', $_SERVER['HTTP_AUTHORIZATION']);
    } elseif (!empty($_SERVER['HTTP_X_API_KEY'])) {
        $received = $_SERVER['HTTP_X_API_KEY'];
    }

    if (!hash_equals($expected, $received)) {
        $logger->warning('Invalid API key attempt');
        json_response(['success' => false, 'error' => 'Unauthorized: sai hoặc thiếu API key'], 401);
    }
}

function save_uploads(string $dataDir, string $timestamp, Logger $logger): array
{
    $savedInfo = [];

    if (!empty($_FILES)) {
        foreach ($_FILES as $fieldName => $file) {
            if ($file['error'] !== UPLOAD_ERR_OK) {
                $logger->warning("Upload error for field $fieldName: " . $file['error']);
                continue;
            }

            $safeName = preg_replace('/[^A-Za-z0-9._-]/', '_', basename($file['name']));
            $destPath = "{$dataDir}/{$timestamp}_{$safeName}";

            if (move_uploaded_file($file['tmp_name'], $destPath)) {
                $savedInfo[] = $destPath;
                $logger->info("File uploaded: {$safeName}");
            }
        }
    }

    return $savedInfo;
}

function save_raw_body(string $dataDir, string $timestamp, Logger $logger): array
{
    $savedInfo = [];
    $rawBody = file_get_contents('php://input');

    if ($rawBody !== '' && empty($_FILES)) {
        $ext = 'json';
        json_decode($rawBody);
        if (json_last_error() !== JSON_ERROR_NONE) {
            $ext = 'txt';
        }

        $destPath = "{$dataDir}/{$timestamp}_upload.{$ext}";
        file_put_contents($destPath, $rawBody);
        $savedInfo[] = $destPath;
        $logger->info("Raw body saved as {$ext}");
    }

    return $savedInfo;
}

// ==================== ROUTER ====================
$router = new Router();

// Home / Health-check
$router->map('GET', '/', function () {
    json_response([
        'success' => true,
        'message' => 'PHP server đang chạy',
        'endpoint' => '/api/highlights',
    ]);
});

// API Endpoint
$router->map('POST', '/api/highlights', function () use ($apiKey, $dataDir, $logger) {
    check_api_key($apiKey, $logger);

    $timestamp = date('Y-m-d_H-i-s');
    $savedInfo = [];

    // Save file uploads
    $savedInfo = array_merge($savedInfo, save_uploads($dataDir, $timestamp, $logger));

    // Save raw body
    $savedInfo = array_merge($savedInfo, save_raw_body($dataDir, $timestamp, $logger));

    if (empty($savedInfo)) {
        $logger->warning('No data received in request');
        json_response(['success' => false, 'error' => 'Không có dữ liệu nào được gửi lên'], 400);
    }

    $logger->info('Data saved successfully', ['files' => count($savedInfo)]);
    json_response([
        'success' => true,
        'message' => 'Đã lưu dữ liệu thành công',
        'saved_files' => array_map('basename', $savedInfo),
        'timestamp' => $timestamp,
    ]);
});

// Match và execute route
$match = $router->match();

if ($match) {
    call_user_func_array($match['target'], $match['params']);
} else {
    json_response(['success' => false, 'error' => 'Not found'], 404);
}
