"""严格编码可信维护状态；正文不能形成可执行的状态标记。"""
import base64
import datetime
import json
import re

_REQUIRED = {'status', 'phase', 'kind', 'reason', 'input_hash', 'run_url', 'updated_at'}
_OPTIONAL = {'change_name', 'invocation', 'implementation_approved', 'last_retry_id',
             'resume_phase', 'plan_paths', 'plan_digest', 'approval_token', 'scheme_decision'}
_PREFIX = '<!-- c2s-state-v1: '


def _validate(state):
    if not isinstance(state, dict) or not _REQUIRED <= state.keys() or state.keys() - _REQUIRED - _OPTIONAL:
        raise ValueError('维护状态字段不完整或未知')
    if state['status'] not in {'completed', 'blocked', 'awaiting-decision'} or state['phase'] not in {'plan', 'smoke', 'blocked'}:
        raise ValueError('维护状态或阶段无效')
    if not isinstance(state['kind'], str) or state['kind'] not in {'plan', 'discuss', 'feature', 'implement', 'bug', 'smoke'}:
        raise ValueError('维护类型无效')
    if state['reason'] is not None and (not isinstance(state['reason'], str) or len(state['reason']) > 4096):
        raise ValueError('维护原因无效')
    if not isinstance(state['input_hash'], str) or not re.fullmatch(r'[0-9a-f]{64}', state['input_hash']):
        raise ValueError('输入指纹无效')
    if not isinstance(state['run_url'], str) or not re.fullmatch(r'https://github.com/[\w.-]+/[\w.-]+/actions/runs/[0-9]+', state['run_url']):
        raise ValueError('运行地址无效')
    stamp = datetime.datetime.fromisoformat(state['updated_at'])
    if stamp.tzinfo is None:
        raise ValueError('状态时间必须包含时区')
    for key in _OPTIONAL & state.keys():
        value = state[key]
        if key == 'implementation_approved':
            if value is not False:
                raise ValueError('当前Runner不授权实施')
        elif key == 'plan_paths':
            if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
                raise ValueError('规划路径无效')
        elif key == 'scheme_decision':
            if not isinstance(value, (dict, str, type(None))):
                raise ValueError('方案决定无效')
        elif value is not None and (not isinstance(value, (str, int)) or isinstance(value, bool)):
            raise ValueError('维护扩展字段无效')
    return state


def encode_state(state):
    raw = json.dumps(_validate(state), ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    if len(raw) > 32768:
        raise ValueError('维护状态过长')
    return _PREFIX + base64.urlsafe_b64encode(raw).decode() + ' -->'


def decode_state(marker):
    if not isinstance(marker, str) or len(marker) > 45000:
        return None
    match = re.fullmatch(re.escape(_PREFIX) + r'([A-Za-z0-9_=-]+) -->', marker)
    if not match:
        return None
    try:
        raw = base64.b64decode(match.group(1), altchars=b'-_', validate=True)
        state = _validate(json.loads(raw))
        return state if encode_state(state) == marker else None
    except (ValueError, TypeError, KeyError, UnicodeError):
        return None
