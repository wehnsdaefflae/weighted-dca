<?php
/**
 * Fetch current ETF prices from Yahoo Finance.
 * Also updates the historical dataset with any new completed months.
 *
 * GET /api/prices.php           → current SWRD.L + EIMI.L prices
 * GET /api/prices.php?update=1  → also update historical data
 */
header('Content-Type: application/json');
header('Cache-Control: no-cache');

$dataDir = __DIR__ . '/../data';
$pricesFile = $dataDir . '/prices.json';
$configFile = $dataDir . '/config.json';

// --- Yahoo Finance fetcher ---
function yahooChart(string $ticker, string $range = '5d', string $interval = '1d'): ?array {
    $url = "https://query1.finance.yahoo.com/v8/finance/chart/{$ticker}?"
         . http_build_query(['range' => $range, 'interval' => $interval]);

    $headers = [
        "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept: application/json",
    ];

    // Try curl first, fall back to file_get_contents
    if (function_exists('curl_init')) {
        $ch = curl_init();
        curl_setopt_array($ch, [
            CURLOPT_URL => $url,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT => 15,
            CURLOPT_HTTPHEADER => $headers,
            CURLOPT_FOLLOWLOCATION => true,
        ]);
        $resp = curl_exec($ch);
        $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        if ($code !== 200 || !$resp) return null;
    } else {
        $ctx = stream_context_create(['http' => [
            'header' => implode("\r\n", $headers) . "\r\n",
            'timeout' => 15,
        ]]);
        $resp = @file_get_contents($url, false, $ctx);
        if (!$resp) return null;
    }

    $data = json_decode($resp, true);
    return $data['chart']['result'][0] ?? null;
}

// --- Get current prices ---
$swrd = yahooChart('SWRD.L');
$eimi = yahooChart('EIMI.L');

$currentSwrd = $swrd['meta']['regularMarketPrice'] ?? null;
$currentEimi = $eimi['meta']['regularMarketPrice'] ?? null;

if (!$currentSwrd || !$currentEimi) {
    http_response_code(502);
    echo json_encode(['error' => 'Failed to fetch prices from Yahoo Finance']);
    exit;
}

// --- Update historical dataset if requested ---
$updated = 0;
if (isset($_GET['update']) && file_exists($configFile)) {
    $config = json_decode(file_get_contents($configFile), true);
    if ($config) {
        $updated = updateHistorical($config, $pricesFile);
    }
}

echo json_encode([
    'SWRD.L' => round($currentSwrd, 4),
    'EIMI.L' => round($currentEimi, 4),
    'timestamp' => date('c'),
    'newMonths' => $updated,
]);

// --- Historical data updater ---
function updateHistorical(array $config, string $pricesFile): int {
    // Fetch ~12 months of monthly data for both trackers
    $iwda = yahooChart('IWDA.L', '1y', '1mo');
    $eimiM = yahooChart('EIMI.L', '1y', '1mo');

    if (!$iwda || !$eimiM) return 0;

    $iwdaTs = $iwda['timestamp'] ?? [];
    $iwdaClose = $iwda['indicators']['quote'][0]['close'] ?? [];
    $eimiTs = $eimiM['timestamp'] ?? [];
    $eimiClose = $eimiM['indicators']['quote'][0]['close'] ?? [];

    // Build EIMI lookup by YYYY-MM
    $eimiByMonth = [];
    foreach ($eimiTs as $i => $ts) {
        if (!$eimiClose[$i]) continue;
        $eimiByMonth[date('Y-m', $ts)] = $eimiClose[$i];
    }

    $firstIWDA = $config['firstIWDA'] ?? null;
    $firstEIMI = $config['firstEIMI'] ?? null;
    if (!$firstIWDA || !$firstEIMI) return 0;

    // Load existing data with file locking
    $fp = fopen($pricesFile, 'c+');
    if (!$fp || !flock($fp, LOCK_EX)) return 0;

    $contents = stream_get_contents($fp);
    $data = $contents ? json_decode($contents, true) : [];
    if (!is_array($data)) $data = [];

    $existingDates = array_flip(array_column($data, 'd'));
    $added = 0;
    $currentMonth = date('Y-m');

    foreach ($iwdaTs as $i => $ts) {
        $month = date('Y-m', $ts);
        $dateStr = date('Y-m-t', $ts); // last day of month

        // Skip current (incomplete) month and already-existing dates
        if ($month === $currentMonth) continue;
        if (isset($existingDates[$dateStr])) continue;
        if (!$iwdaClose[$i] || !isset($eimiByMonth[$month])) continue;

        // Compute portfolio index (same formula as Python portfolio_monthly)
        $wNorm = ($iwdaClose[$i] / $firstIWDA) * 100;
        $eNorm = ($eimiByMonth[$month] / $firstEIMI) * 100;
        $portfolio = 0.7 * $wNorm + 0.3 * $eNorm;

        $data[] = ['d' => $dateStr, 'p' => round($portfolio, 4)];
        $added++;
    }

    if ($added > 0) {
        usort($data, function ($a, $b) { return strcmp($a['d'], $b['d']); });
        ftruncate($fp, 0);
        rewind($fp);
        fwrite($fp, json_encode($data));
    }

    flock($fp, LOCK_UN);
    fclose($fp);
    return $added;
}
