<?php

declare(strict_types=1);

/**
 * Plugin Name: Error Reporting Manager
 * Description: Custom error reporting configuration for WordPress
 * Version: 1.0.0
 * Author: SymPress
 *
 * We create an early callback to bypass the error reporting
 * setup in wp_debug_mode() to hide E_DEPRECATED and E_USER_DEPRECATED
 * errors as there will be a lot at the moment
 *
 * @see wp_debug_mode()
 */

namespace SymPress\Starter\Debug;

if (!defined('ABSPATH')) {
    exit;
}

set_error_handler(
    static fn ($errno, $errstr, $errfile, $errline): bool => ($errno === E_DEPRECATED || $errno === E_USER_DEPRECATED)
        && !filter_var(getenv('SYMPRESS_DISPLAY_DEPRECATED'), FILTER_VALIDATE_BOOLEAN),
);

final class ErrorReportingManager
{
    private const BYPASS_REQUEST_TYPES = [
        'XMLRPC_REQUEST',
        'REST_REQUEST',
        'MS_FILES_REQUEST',
        'WP_INSTALLING',
        'DOING_AJAX',
    ];

    private const string JSON_CONTENT_TYPE_PATTERN = '/(^|\s|,)application\/([\w!#$&-^.]+\+)?json(\+oembed)?($|\s|;|,)/i';

    public static function initialize(): void
    {
        self::setupEarlyErrorReporting();
        self::registerDebugModeHook();
    }

    private static function setupEarlyErrorReporting(): void
    {
        if (!self::isDebugEnabled()) {
            return;
        }

        error_reporting(self::getErrorReportingLevel());
    }

    private static function registerDebugModeHook(): void
    {
        if (!isset($GLOBALS['wp_filter']['enable_wp_debug_mode_checks'][10])) {
            $GLOBALS['wp_filter']['enable_wp_debug_mode_checks'][10] = [];
        }

        $GLOBALS['wp_filter']['enable_wp_debug_mode_checks'][10][] = [
            'accepted_args' => 0,
            'function'      => [self::class, 'handleDebugMode'],
        ];
    }

    public static function handleDebugMode(): false
    {
        if (self::shouldBypassDisplay()) {
            ini_set('display_errors', '0');
            return false;
        }

        if (self::isDebugEnabled()) {
            self::configureDebugMode();
            return false;
        }

        error_reporting(self::getProductionErrorLevel());

        return false;
    }

    private static function shouldBypassDisplay(): bool
    {
        if (self::isSpecialRequestType()) {
            return true;
        }

        return self::isJsonRequest();
    }

    private static function isSpecialRequestType(): bool
    {
        return array_any(
            self::BYPASS_REQUEST_TYPES,
            static fn ($constant) => defined($constant) && constant($constant),
        );
    }

    private static function isJsonRequest(): bool
    {
        $headers = ['HTTP_ACCEPT', 'CONTENT_TYPE'];

        return array_any(
            $headers,
            static fn ($header) => self::hasJsonContentType($header),
        );
    }

    private static function hasJsonContentType(string $header): bool
    {
        $value = filter_input(INPUT_SERVER, $header, FILTER_SANITIZE_FULL_SPECIAL_CHARS);

        if ($value === null || $value === false) {
            return false;
        }

        return preg_match(self::JSON_CONTENT_TYPE_PATTERN, $value) === 1;
    }

    private static function configureDebugMode(): void
    {
        error_reporting(self::getErrorReportingLevel());

        self::configureDisplayErrors();
        self::configureErrorLog();
    }

    private static function configureDisplayErrors(): void
    {
        if (!defined('WP_DEBUG_DISPLAY')) {
            return;
        }

        $displayValue = WP_DEBUG_DISPLAY ? '1' : '0';
        ini_set('display_errors', $displayValue);
    }

    private static function configureErrorLog(): void
    {
        $logPath = self::getErrorLogPath();

        if ($logPath === null) {
            return;
        }

        ini_set('log_errors', '1');
        ini_set('error_log', $logPath);
    }

    private static function getErrorLogPath(): ?string
    {
        if (!defined('WP_DEBUG_LOG')) {
            return null;
        }

        $debugLog = constant('WP_DEBUG_LOG');

        // WP_DEBUG_LOG may be a string path in wp-config.php, even though WordPress stubs narrow it to bool.
        // @phpstan-ignore-next-line
        if (is_string($debugLog)) {
            return $debugLog;
        }

        if (in_array(strtolower((string) $debugLog), ['true', '1'], true)) {
            return WP_CONTENT_DIR . '/debug.log';
        }

        return null;
    }

    private static function isDebugEnabled(): bool
    {
        return defined('WP_DEBUG') && WP_DEBUG;
    }

    private static function getErrorReportingLevel(): int
    {
        if (filter_var(getenv('SYMPRESS_DISPLAY_DEPRECATED'), FILTER_VALIDATE_BOOLEAN)) {
            return E_ALL;
        }

        return E_ALL & ~E_NOTICE & ~E_DEPRECATED & ~E_USER_DEPRECATED;
    }

    private static function getProductionErrorLevel(): int
    {
        return E_CORE_ERROR
            | E_CORE_WARNING
            | E_COMPILE_ERROR
            | E_ERROR
            | E_WARNING
            | E_PARSE
            | E_USER_ERROR
            | E_USER_WARNING
            | E_RECOVERABLE_ERROR;
    }
}

ErrorReportingManager::initialize();
