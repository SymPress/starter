<?php

/**
 * Plugin Name: Allowed HTML Attributes Manager
 * Description: Manages allowed HTML tags and attributes for WordPress content filtering
 * Version: 1.0.0
 * Author: SymPress
 */

declare(strict_types=1);

namespace SymPress\Starter\Content;

if (!defined('ABSPATH')) {
    exit;
}

final class AllowedHtmlAttributesManager
{
    private const ADDITIONAL_TAGS = [
        'source' => [
            'src'  => [],
            'type' => [],
        ],
    ];

    private function __construct()
    {
    }

    public static function initialize(): void
    {
        add_filter('wp_kses_allowed_html', [self::class, 'addAllowedTags'], 10, 2);
    }

    /**
     * @param array<string, mixed> $tags
     * @return array<string, mixed>
     */
    public static function addAllowedTags(array $tags, string $context): array
    {
        if ($context !== 'post') {
            return $tags;
        }

        return array_merge($tags, self::ADDITIONAL_TAGS);
    }
}

AllowedHtmlAttributesManager::initialize();
