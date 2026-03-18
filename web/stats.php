<?php
/**
 * Statistics Dashboard (stats.php)
 * Parses tracking.log to display product-wise click counts within a date range.
 */

date_default_timezone_set('Asia/Seoul');
$log_file = 'tracking.log';
$start_date = isset($_GET['start']) ? $_GET['start'] : date('Y-m-d', strtotime('-1 month'));
$end_date = isset($_GET['end']) ? $_GET['end'] : date('Y-m-d');

$stats = [];
$total_clicks = 0;

if (file_exists($log_file)) {
    $handle = fopen($log_file, "r");
    if ($handle) {
        while (($line = fgets($handle)) !== false) {
            // Regex to parse: [Y-m-d H:i:s] IP | Product | URL
            if (preg_match('/^\[(.*?)\] (.*?) \| (.*?) \| (.*?)$/', $line, $matches)) {
                $timeraw = $matches[1];
                $product = trim($matches[3]);
                $item_date = date('Y-m-d', strtotime($timeraw));

                if ($item_date >= $start_date && $item_date <= $end_date) {
                    if (!isset($stats[$product])) {
                        $stats[$product] = 0;
                    }
                    $stats[$product]++;
                    $total_clicks++;
                }
            }
        }
        fclose($handle);
    }
}

// Sort by click count descending
arsort($stats);
?>
<!DOCTYPE html>
<html lang="ko">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>트래픽 통계 대시보드</title>
    <style>
        body {
            font-family: 'Pretendard', sans-serif;
            background: #F7FAFC;
            color: #2D3748;
            padding: 2rem;
        }

        .container {
            max-width: 800px;
            margin: 0 auto;
            background: #FFF;
            padding: 2rem;
            border-radius: 1rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        }

        h1 {
            margin-bottom: 2rem;
            font-size: 1.5rem;
            text-align: center;
        }

        .filter-form {
            display: flex;
            gap: 1rem;
            justify-content: center;
            margin-bottom: 2rem;
            align-items: flex-end;
        }

        .form-group {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        input[type="date"] {
            padding: 0.5rem;
            border: 1px solid #E2E8F0;
            border-radius: 0.5rem;
        }

        button {
            padding: 0.5rem 1.5rem;
            background: #3366FF;
            color: white;
            border: none;
            border-radius: 0.5rem;
            cursor: pointer;
            height: 38px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
        }

        th,
        td {
            padding: 1rem;
            text-align: left;
            border-bottom: 1px solid #E2E8F0;
        }

        th {
            background: #F8FAFF;
            font-weight: 600;
        }

        .count-badge {
            background: #EBF1FF;
            color: #3366FF;
            padding: 0.25rem 0.75rem;
            border-radius: 1rem;
            font-weight: 700;
        }

        .summary {
            margin-top: 1.5rem;
            text-align: right;
            font-weight: 600;
            color: #4A5568;
        }
    </style>
</head>

<body>

    <div class="container">
        <h1>📊 제품별 클릭 통계</h1>

        <form class="filter-form" method="GET">
            <div class="form-group">
                <label>시작일</label>
                <input type="date" name="start" value="<?php echo $start_date; ?>">
            </div>
            <div class="form-group">
                <label>종료일</label>
                <input type="date" name="end" value="<?php echo $end_date; ?>">
            </div>
            <button type="submit">조회</button>
        </form>

        <table>
            <thead>
                <tr>
                    <th>제품명</th>
                    <th style="width: 120px;">클릭 수</th>
                </tr>
            </thead>
            <tbody>
                <?php if (empty($stats)): ?>
                    <tr>
                        <td colspan="2" style="text-align: center; color: #A0AEC0; padding: 3rem;">해당 기간의 데이터가 없습니다.</td>
                    </tr>
                <?php else: ?>
                    <?php foreach ($stats as $name => $count): ?>
                        <tr>
                            <td>
                                <?php echo htmlspecialchars($name); ?>
                            </td>
                            <td><span class="count-badge">
                                    <?php echo $count; ?>
                                </span></td>
                        </tr>
                    <?php endforeach; ?>
                <?php endif; ?>
            </tbody>
        </table>

        <div class="summary">
            총 클릭 수:
            <?php echo $total_clicks; ?> 건
        </div>
    </div>

</body>

</html>