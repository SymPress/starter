#!/usr/bin/env python3
"""Render production config for a reviewed installation; does not install/reload."""
import argparse
from pathlib import Path
import re

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--hostname', required=True)
p.add_argument('--root', required=True)
p.add_argument('--output', required=True)
p.add_argument('--hsts', action='store_true', help='Enable HSTS after verifying the canonical HTTPS site.')
a = p.parse_args()
if not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?', a.hostname) or '..' in a.hostname:
    p.error('Use a DNS hostname without scheme, port or nginx syntax.')
if not re.fullmatch(r'/[A-Za-z0-9/_-]+', a.root):
    p.error('Use an absolute deployment root containing simple path components.')
source = Path(__file__).parent / 'nginx'
out = Path(a.output)
out.mkdir(parents=True, exist_ok=True)
for name in ('production-server.conf', 'cache-http.conf', 'security.conf', 'security-headers.conf', 'static-assets-cache.conf'):
    text = (source / name).read_text().replace('sympress.example.invalid', a.hostname)
    text = text.replace('/srv/sympress/current', a.root + '/current').replace('/var/www/html', a.root + '/current')
    if a.hsts:
        if name == 'security-headers.conf':
            text += '\nadd_header Strict-Transport-Security "max-age=31536000" always;\n'
    (out / name).write_text(text)
