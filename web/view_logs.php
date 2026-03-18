<?php
/**
 * Simple Viewer for tracking.log
 */
$log_file = 'tracking.log';
?>
<!DOCTYPE html>
<html lang="ko">

<head>
    <meta charset="UTF-8">
    <title>트래픽 통계 - deoklabs.xyz</title>
    <style>
        body {
            font-family: monospace;
            background: #f4f4f4;
            padding: 20px;
            font-size: 14px;
        }

        .log-container {
            background: #fff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            white-space: pre-wrap;
            word-break: break-all;
        }

        h1 {
            font-family: sans-serif;
        }
    </style>
</head>

<body>
    <h1>트래픽 트래킹 기록</h1>
    <div class="log-container">
        <?php
        if (!file_exists($log_file)) {
            echo "아직 기록된 트래픽이 없습니다.";
        } else {
            echo htmlspecialchars(file_get_contents($log_file));
        }
        ?>
    </div>
</body>

</html>