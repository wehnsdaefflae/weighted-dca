<?php
/**
 * Historical price dataset CRUD.
 *
 * GET  /api/data.php  → returns full price array
 * POST /api/data.php  → appends a data point {"d":"YYYY-MM-DD","p":123.45}
 */
header('Content-Type: application/json');
header('Cache-Control: no-cache');

$file = __DIR__ . '/../data/prices.json';

if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    if (file_exists($file)) {
        readfile($file);
    } else {
        echo '[]';
    }
    exit;
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $input = json_decode(file_get_contents('php://input'), true);

    if (!$input || !isset($input['d']) || !isset($input['p'])
        || !preg_match('/^\d{4}-\d{2}-\d{2}$/', $input['d'])
        || !is_numeric($input['p']) || $input['p'] <= 0) {
        http_response_code(400);
        echo json_encode(['error' => 'Invalid data. Expected {"d":"YYYY-MM-DD","p":number}']);
        exit;
    }

    $fp = fopen($file, 'c+');
    if (!$fp || !flock($fp, LOCK_EX)) {
        http_response_code(500);
        echo json_encode(['error' => 'Could not acquire file lock']);
        exit;
    }

    $contents = stream_get_contents($fp);
    $data = $contents ? json_decode($contents, true) : [];
    if (!is_array($data)) $data = [];

    // Check for duplicate month
    $inputMonth = substr($input['d'], 0, 7);
    $replaced = false;
    foreach ($data as &$entry) {
        if (substr($entry['d'], 0, 7) === $inputMonth) {
            $entry['p'] = round($input['p'], 4);
            $replaced = true;
            break;
        }
    }
    unset($entry);

    if (!$replaced) {
        $data[] = ['d' => $input['d'], 'p' => round($input['p'], 4)];
    }

    usort($data, function ($a, $b) { return strcmp($a['d'], $b['d']); });

    ftruncate($fp, 0);
    rewind($fp);
    fwrite($fp, json_encode($data));
    flock($fp, LOCK_UN);
    fclose($fp);

    echo json_encode(['ok' => true, 'count' => count($data), 'replaced' => $replaced]);
    exit;
}

http_response_code(405);
echo json_encode(['error' => 'Method not allowed']);
