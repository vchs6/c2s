"""Small GitHub REST adapter; credential is supplied only by the current job."""
import html
import json
import os
import urllib.error
import urllib.request
from urllib.parse import quote
from .core import has_write
from .state_codec import encode_state


class GitHub:
    def __init__(self):
        self.repo = os.environ['GITHUB_REPOSITORY']
        self.token = os.environ['GH_TOKEN']
        self.base = os.environ.get('GITHUB_API_URL', 'https://api.github.com') + '/repos/' + self.repo
        self.permissions = {}

    def request(self, path, method='GET', data=None):
        raw = json.dumps(data).encode() if data is not None else None
        request = urllib.request.Request(self.base + path, data=raw, method=method, headers={
            'Authorization': 'Bearer ' + self.token, 'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28', 'Content-Type': 'application/json'})
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.load(response) if response.status != 204 else None

    def pages(self, path):
        page, result = 1, []
        while True:
            values = self.request(f'{path}{"&" if "?" in path else "?"}per_page=100&page={page}')
            result.extend(values)
            if len(values) < 100: return result
            page += 1

    def permission(self, login):
        if login.lower() == self.repo.split('/')[0].lower():
            return 'admin'
        if login not in self.permissions:
            try:
                self.permissions[login] = self.request('/collaborators/' + quote(login, safe='') + '/permission')['permission']
            except urllib.error.HTTPError as error:
                if error.code not in {403, 404}: raise
                self.permissions[login] = 'none'
        return self.permissions[login]

    def comments(self, number):
        return self.pages(f'/issues/{number}/comments')

    def feedback(self, number, state):
        marker = encode_state(state)
        labels = {'completed': 'agent:done', 'blocked': 'agent:blocked', 'awaiting-decision': 'agent:awaiting-decision'}
        label = labels[state['status']]
        try:
            self.request('/labels', 'POST', dict(name=label, color='5319e7'))
        except urllib.error.HTTPError as error:
            if error.code != 422: raise
        current = self.request(f'/issues/{number}')
        other = [item['name'] for item in current['labels'] if not item['name'].startswith('agent:')]
        if sorted(item['name'] for item in current['labels']) != sorted(other + [label]):
            self.request(f'/issues/{number}/labels', 'PUT', dict(labels=other + [label]))
        body = '<!-- c2s-worker -->\n' + f"状态：**{state['status']}**；模式：{state['phase']}。\n\n原因：{html.escape(state.get('reason') or '验证通过')}\n\n运行：{state['run_url']}"
        if state.get('approval_token'):
            body += f"\n\n规划指纹：`{html.escape(str(state['approval_token']))}`；只用于追溯，不授权当前Runner实施。方案确认、整体规划审核与开发批准分别处理。"
        if state['status'] == 'blocked':
            body += '\n\n修复原因后，显式手动启动指定Issue的plan或smoke；评论与定时任务不触发恢复。'
        body += '\n\n' + marker
        notes = [c for c in self.comments(number) if c['user'].get('type') == 'Bot' and c.get('body', '').startswith('<!-- c2s-worker -->')]
        if notes:
            if notes[-1]['body'] != body:
                self.request(f"/issues/comments/{notes[-1]['id']}", 'PATCH', dict(body=body))
        else: self.request(f'/issues/{number}/comments', 'POST', dict(body=body))
