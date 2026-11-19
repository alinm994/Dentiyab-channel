"""Sends the dentiyab.ir Telegram channel posts. This small public repository holds only this sender (owner
2026-11-19: GitHub gives public repositories free Actions minutes; the private site repository had used its monthly
minutes). The posts come from the site's read-only list https://dentiyab.ir/staff/telegram/feed.json — only posts
whose time has come, which the channel publishes anyway — and the ids already sent are kept in `sent.json` on the
branch `sent` of this repository, so a post never goes out twice. Secrets (Settings → Secrets → Actions):
TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL (e.g. @dentiyab). Reference copy: alinm994/Dent-market deploy/channel-sender/."""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

SITE = 'https://dentiyab.ir'
AGENT = 'Mozilla/5.0 (compatible; DentiyabCheck/1; channel sender)'
CAPTION_MAX = 1024                  # Telegram's limit for a photo caption; a longer post goes as text


def get(url, timeout=90):
    req = urllib.request.Request(url, headers={'User-Agent': AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def picture(path):
    try:
        data = get(SITE + path, 120)
        return data if data[:3] == b'\xff\xd8\xff' else None
    except Exception as exc:
        print('no picture:', type(exc).__name__, str(exc)[:120])
        return None


def send(token, chat, text, photo):
    base = f'https://api.telegram.org/bot{token}'
    if photo and len(text) <= CAPTION_MAX:
        boundary = 'dentiyab' + str(int(time.time() * 1000))
        body = b''
        for k, v in (('chat_id', chat), ('caption', text)):
            body += f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
        body += (f'--{boundary}\r\nContent-Disposition: form-data; name="photo"; filename="post.jpg"\r\n'
                 'Content-Type: image/jpeg\r\n\r\n').encode() + photo + f'\r\n--{boundary}--\r\n'.encode()
        req = urllib.request.Request(base + '/sendPhoto', data=body,
                                     headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
    else:
        req = urllib.request.Request(base + '/sendMessage', data=urllib.parse.urlencode({'chat_id': chat, 'text': text}).encode())
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return json.loads(r.read() or b'{}').get('ok') is True, ''
    except Exception as exc:                      # the answer explains a wrong token/channel; never print the token
        body = getattr(exc, 'read', lambda: b'')()[:300].decode('utf-8', 'replace')
        return False, f'{type(exc).__name__} {body}'


def slot(post_id):
    """«2026-11-19-09» of «2026-11-19-09-deal»: one post per date and hour."""
    return '-'.join(post_id.split('-')[:4])


def main(sent_path):
    token, chat = os.environ.get('TELEGRAM_BOT_TOKEN', ''), os.environ.get('TELEGRAM_CHANNEL', '')
    if not token or not chat:
        sys.exit('Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL in Settings → Secrets and variables → Actions.')
    if not (chat.startswith(('@', '-')) or chat.lstrip('-').isdigit()):
        chat = '@' + chat
    sent = json.load(open(sent_path)) if os.path.exists(sent_path) else []
    query = '?all=1' if os.environ.get('SEND_ALL') == '1' else ''
    items = json.loads(get(f'{SITE}/staff/telegram/feed.json{query}')).get('items', [])
    print(len(items), 'due')
    for item in items:
        if item['id'] in sent or any(slot(s) == slot(item['id']) for s in sent):
            print('already sent', item['id'])
            continue
        ok, why = send(token, chat, item['text'], picture(item['picture']))
        print(('sent ' if ok else 'NOT sent ') + item['id'] + (f' — {why}' if why else ''))
        if ok:
            sent.append(item['id'])
            json.dump(sent[-500:], open(sent_path, 'w'), indent=1)
        time.sleep(5)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'sent.json')
