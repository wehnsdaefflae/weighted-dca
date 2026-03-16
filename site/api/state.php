<?php
/**
 * Investment state persistence.
 *
 * GET  /api/state.php  → returns {params, log}
 * POST /api/state.php  → saves {params, log}
 */
header('Content-Type: application/json');
header('Cache-Control: no-cache');

$file = __DIR__ . '/../data/state.json';

if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    if (file_exists($file)) {
        readfile($file);
    } else {
        echo json_encode(['params' => null, 'log' => []]);
    }
    exit;
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $raw = file_get_contents('php://input');
    $data = json_decode($raw, true);

    if (!$data || !is_array($data)) {
        http_response_code(400);
        echo json_encode(['error' => 'Invalid JSON']);
        exit;
    }

    // Basic validation: must have params and/or log
    if (!isset($data['params']) && !isset($data['log'])) {
        http_response_code(400);
        echo json_encode(['error' => 'Expected {params, log}']);
        exit;
    }

    // Size guard: reject payloads > 1MB
    if (strlen($raw) > 1048576) {
        http_response_code(413);
        echo json_encode(['error' => 'Payload too large']);
        exit;
    }

    $fp = fopen($file, 'c');
    if (!$fp || !flock($fp, LOCK_EX)) {
        http_response_code(500);
        echo json_encode(['error' => 'Could not acquire file lock']);
        exit;
    }

    ftruncate($fp, 0);
    rewind($fp);
    fwrite($fp, json_encode($data, JSON_PRETTY_PRINT));
    flock($fp, LOCK_UN);
    fclose($fp);

    echo json_encode(['ok' => true]);
    exit;
}

http_response_code(405);
echo json_encode(['error' => 'Method not allowed']);
