<?php

declare(strict_types=1);

// Run before Composer boot. Never print or rotate an existing site key.
(static function (): void {
    if (PHP_SAPI !== 'cli') {
        throw new RuntimeException('Environment preparation requires CLI.');
    }
    $path = dirname(__DIR__) . '/.env';
    if (!is_file($path) || is_link($path)) {
        throw new RuntimeException('Create a regular .env from .env.example first.');
    }
    $stream = fopen($path, 'r+');
    if ($stream === false || !flock($stream, LOCK_EX)) {
        throw new RuntimeException('Cannot lock the private environment file.');
    }
    try {
        if (!chmod($path, 0600)) {
            throw new RuntimeException('Cannot protect the private environment file.');
        }
        $contents = stream_get_contents($stream);
        if (!is_string($contents)) {
            throw new RuntimeException('Cannot read the private environment file.');
        }
        $configured = static function (array $names) use ($contents): bool {
            foreach ($names as $name) {
                $processValue = getenv($name);
                if (is_string($processValue) && $processValue !== '') {
                    return true;
                }
                preg_match_all('/^\h*(?:export\h+)?' . preg_quote($name, '/') . '\h*=([^\r\n]*)/m', $contents, $matches);
                foreach ($matches[1] as $value) {
                    if (preg_match('/^(?:#.*|(?:""|\'\')(?:\h+#.*)?)?$/D', trim($value)) !== 1) {
                        return true;
                    }
                }
            }
            return false;
        };
        $lines = [];
        if (!$configured(['APP_SECRET', 'APP_SECRET_FILE'])) {
            $lines[] = 'APP_SECRET=' . bin2hex(random_bytes(32));
        }
        if (!$configured(['SYMPRESS_PROJECT_DIR'])) {
            // This literal identity survives release symlinks; deploy.php supplies the deployment base.
            $identity = dirname(__DIR__);
            // Dotenv single quotes are literal: backslashes cannot escape an apostrophe.
            $quoted = "'" . str_replace(["'", "\r", "\n"], ["'\"'\"'", "'\"\\r\"'", "'\"\\n\"'"], $identity) . "'";
            $lines[] = 'SYMPRESS_PROJECT_DIR=' . $quoted;
        }
        if ($lines === []) {
            return;
        }
        $addition = ($contents === '' || str_ends_with($contents, "\n") ? '' : "\n")
            . implode("\n", $lines) . "\n";
        if (fseek($stream, 0, SEEK_END) !== 0 || fwrite($stream, $addition) !== strlen($addition) || !fflush($stream)) {
            throw new RuntimeException('Cannot persist the private site environment.');
        }
    } finally {
        flock($stream, LOCK_UN);
        fclose($stream);
    }
})();
