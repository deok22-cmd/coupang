<?php
/**
 * Coupang Partners Bridge Page (go.php)
 * This script provides a professional landing page before redirecting to Coupang.
 */

// Basic link validation and getting the target URL
$target_url = isset($_GET['url']) ? $_GET['url'] : 'https://www.coupang.com';
$product_name_raw = isset($_GET['name']) ? $_GET['name'] : '선택하신 상품';
$product_name = htmlspecialchars($product_name_raw);

// --- Tracking Logic ---
date_default_timezone_set('Asia/Seoul');
$log_file = 'tracking.log';
$current_time = date('Y-m-d H:i:s');
$user_ip = $_SERVER['REMOTE_ADDR'];
$log_entry = sprintf("[%s] %s | %s | %s\n", $current_time, $user_ip, $product_name_raw, $target_url);
file_put_contents($log_file, $log_entry, FILE_APPEND);
// ----------------------
?>
<!DOCTYPE html>
<html lang="ko">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo $product_name; ?> - 최저가 확인하기</title>
    <style>
        :root {
            --primary: #3366FF;
            --primary-hover: #254EDB;
            --bg-gradient: linear-gradient(135deg, #f8faff 0%, #ffffff 100%);
            --text-main: #1A202C;
            --text-sub: #4A5568;
            --white: #FFFFFF;
            --shadow: 0 10px 25px rgba(51, 102, 255, 0.1);
        }

        body {
            margin: 0;
            padding: 0;
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif;
            background: var(--bg-gradient);
            color: var(--text-main);
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            overflow: hidden;
        }

        .container {
            max-width: 480px;
            width: 90%;
            background: var(--white);
            padding: 2.5rem;
            border-radius: 2rem;
            box-shadow: var(--shadow);
            text-align: center;
            animation: slideUp 0.6s ease-out;
            border: 1px solid rgba(51, 102, 255, 0.05);
        }

        @keyframes slideUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }

            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .icon-box {
            width: 80px;
            height: 80px;
            background: rgba(51, 102, 255, 0.08);
            border-radius: 1.5rem;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 1.5rem;
        }

        .icon-box svg {
            width: 40px;
            height: 40px;
            color: var(--primary);
        }

        h1 {
            font-size: 1.5rem;
            font-weight: 700;
            margin-bottom: 0.75rem;
            line-height: 1.4;
        }

        p {
            color: var(--text-sub);
            font-size: 0.95rem;
            margin-bottom: 2rem;
            line-height: 1.6;
        }

        .product-badge {
            display: inline-block;
            background: #EBF1FF;
            color: var(--primary);
            padding: 0.4rem 1rem;
            border-radius: 2rem;
            font-size: 0.8rem;
            font-weight: 600;
            margin-bottom: 1.5rem;
        }

        .btn {
            display: flex;
            align-items: center;
            justify-content: center;
            background: var(--primary);
            color: var(--white);
            text-decoration: none;
            padding: 1.2rem;
            border-radius: 1rem;
            font-size: 1.1rem;
            font-weight: 700;
            transition: all 0.3s ease;
            box-shadow: 0 4px 12px rgba(51, 102, 255, 0.2);
        }

        .btn:hover {
            background: var(--primary-hover);
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(51, 102, 255, 0.3);
        }

        .timer {
            margin-top: 1.5rem;
            font-size: 0.85rem;
            color: #A0AEC0;
        }

        .footer-note {
            margin-top: 2.5rem;
            font-size: 0.75rem;
            color: #CBD5E0;
        }
    </style>
</head>

<body>

    <div class="container">
        <div class="icon-box">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z">
                </path>
            </svg>
        </div>

        <div class="product-badge">공식 파트너 연결</div>

        <h1><?php echo $product_name; ?></h1>
        <p>요청하신 상품의 쿠팡 페이지로 안전하게 연결해 드립니다. <br>최저가와 혜택을 즉시 확인해보세요.</p>

        <a href="<?php echo $target_url; ?>" class="btn" id="redirect-btn">
            쿠팡에서 최저가 확인하기
        </a>

        <div class="timer">
            잠시 후 자동으로 이동합니다 (<span id="countdown">3</span>초)
        </div>

        <div class="footer-note">
            본 전송 시스템은 정식 파트너스 활동의 일환으로 안전하게 운영됩니다.
        </div>
    </div>

    <script>
        let seconds = 3;
        const countdownEl = document.getElementById('countdown');
        const targetUrl = "<?php echo $target_url; ?>";

        const timer = setInterval(() => {
            seconds--;
            countdownEl.textContent = seconds;
            if (seconds <= 0) {
                clearInterval(timer);
                window.location.href = targetUrl;
            }
        }, 1000);

        // Track click event (Optional: if you have a tracking API)
        document.getElementById('redirect-btn').addEventListener('click', () => {
            // console.log('Link clicked');
        });
    </script>

</body>

</html>