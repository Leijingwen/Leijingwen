"""Generate local profile cards using public GitHub API data. Python standard library only."""

import json
import os
from collections import Counter
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
COLORS = ['#67E8F9', '#A5B4FC', '#FBBF24', '#F9A8D4', '#6EE7B7']


def api(path):
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'profile-cards'}
    token = os.environ.get('GH_TOKEN')
    if token:
        headers['Authorization'] = f'Bearer {token}'
    with urlopen(Request('https://api.github.com' + path, headers=headers), timeout=30) as response:
        return json.load(response)


def text(x, y, value, size=14, color='#C7D2FE'):
    return f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}">{escape(str(value))}</text>'


def card(title, description, body, footer):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="240" viewBox="0 0 480 240" role="img">'
        f'<title>{escape(title)}</title><desc>{escape(description)}</desc>'
        '<rect width="480" height="240" rx="16" fill="#0B1020"/>'
        '<path d="M24 56H456" stroke="#253353"/>'
        '<g font-family="Segoe UI,Arial,sans-serif">'
        + text(24, 36, title, 19, '#67E8F9') + body
        + text(24, 222, footer, 11, '#94A3B8') + '</g></svg>\n'
    )


def generate(user, repos, languages, updated):
    original = [repo for repo in repos if not repo['fork']]
    metrics = [
        ('Public repositories', len(repos)),
        ('Stars on original repos', sum(repo['stargazers_count'] for repo in original)),
        ('Forks of original repos', sum(repo['forks_count'] for repo in original)),
        ('Followers', user['followers']),
    ]
    body = ''.join(text(24, 86 + i * 34, label) + text(410, 86 + i * 34, count, 18, '#E6F7FF')
                   for i, (label, count) in enumerate(metrics))
    stats = card('GitHub statistics', '; '.join(f'{k}: {v}' for k, v in metrics), body, updated)
    top = languages.most_common(5)
    total = sum(languages.values())
    body = ''
    for i, (name, count) in enumerate(top):
        percent = count / total * 100
        y = 78 + i * 27
        body += text(24, y, name, 13) + text(399, y, f'{percent:.1f}%', 12)
        body += f'<rect x="150" y="{y - 9}" width="{max(1, percent * 2.2):.1f}" height="8" rx="4" fill="{COLORS[i]}"/>'
    if not top:
        body = text(24, 100, 'No public language data yet.')
    language_card = card('Top languages', 'Language share by bytes in public, non-fork repositories.',
                         body, 'Public original repos · bytes · ' + updated)
    return stats, language_card


def main():
    username = os.environ.get('PROFILE_USER', 'Leijingwen')
    user = api(f'/users/{username}')
    repos = []
    page = 1
    while True:
        batch = api(f'/users/{username}/repos?per_page=100&type=owner&page={page}')
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    languages = Counter()
    for repo in repos:
        if not repo['fork']:
            languages.update(api(f'/repos/{repo["full_name"]}/languages'))
    updated = datetime.now(timezone.utc).strftime('Updated %Y-%m-%d UTC')
    stats, language_card = generate(user, repos, languages, updated)
    assets = ROOT / 'assets'
    assets.mkdir(exist_ok=True)
    # Fetch everything before writing so API errors preserve the previous cards.
    (assets / 'stats.svg').write_text(stats, encoding='utf-8')
    (assets / 'languages.svg').write_text(language_card, encoding='utf-8')


if __name__ == '__main__':
    main()
