"""Reminder lifecycle shared by the trusted bot, local CLI and hosted assistant."""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from . import assistant, assistant_agent as a
from .database import now_iso

ZONE = ZoneInfo('Asia/Shanghai')


def now():
    return datetime.now(ZONE)


def capabilities():
    return {
        'version': 'assistant-controls-v2',
        'watch_kinds': {
            'price': '到价提醒，价格与方向必需；持续跟踪，离开区间后再次进入会再提醒',
            'date': '指定日期的一次提醒；北京时间，未给时间默认09:00；不代表财报已发布',
            'research': '库内新财报数据或公告变化；不是日期闹钟，不是用户笔记变化',
            'response': '应对结论或复核状态变化',
        },
        'operations': list(a.Command.model_fields['operation'].annotation.__args__),
        'confirmation': '明确条件直接watch；提出选项先prepare_watch，用户下一条确认后confirm_watch；不能用模型text冒充原话',
        'management': 'list_watches查全部或按公司筛选；watch加record_id改条件；pause_watch/resume_watch停用恢复；cancel取消草稿',
        'limits': ['未连接券商，不自动下单', '本地助手与API需持续运行，离线期间无法准点推送', '研究提醒依赖数据同步，投递成功不代表用户已读'],
    }


def normalize_due(value: str) -> datetime:
    value = value.strip()
    if re.fullmatch(r'\d{2}-\d{2}(?:[ T]\d{2}:\d{2})?', value):
        value = f'{now().year}-' + value
    try:
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            value += 'T09:00:00'
        due = datetime.fromisoformat(value)
        due = due.replace(tzinfo=ZONE) if due.tzinfo is None else due.astimezone(ZONE)
    except ValueError as exc:
        raise a.AgentError('提醒时间请用日期和可选时分，例如10-20或2026-10-20 09:00。', 'INVALID_REMINDER_TIME') from exc
    due = due.replace(second=0, microsecond=0)
    if due <= now():
        raise a.AgentError('这个提醒时间已经过去，请明确新的日期或时间；不会自动顺延到明年。', 'REMINDER_IN_PAST')
    return due


def listing(conn, company_id=None):
    rows = conn.execute('''SELECT s.*, c.name, c.symbol FROM assistant_subscriptions s
        JOIN companies c ON c.id=s.company_id AND c.user_id=s.user_id
        WHERE s.user_id=?''' + (' AND s.company_id=?' if company_id else '') + ' ORDER BY s.id',
        (a._scope(), company_id) if company_id else (a._scope(),)).fetchall()
    alerts = conn.execute('SELECT id,levels,delivery,delivery_error,delivered_at,created_at FROM assistant_alerts WHERE user_id=? AND kind=\'subscription\' ORDER BY id DESC LIMIT 200', (a._scope(),)).fetchall()
    latest = {}
    for alert in alerts:
        for part in a._load(alert['levels'] or '[]'):
            latest.setdefault(part['subscription_id'], dict(alert))
    result = []
    for row in rows:
        r = dict(row); snapshot = a._load(r.pop('snapshot')); r.pop('user_id', None)
        r['remind_at'] = snapshot.get('remind_at') if r['kind'] == 'date' else None
        r['state'] = ('queued' if r['inside'] else 'scheduled') if r['kind'] == 'date' else 'active'
        if not r['enabled']:
            r['state'] = 'paused'
        alert = latest.get(r['id'])
        r['last_delivery'] = {k: alert[k] for k in ('id', 'delivery', 'delivery_error', 'delivered_at', 'created_at')} if alert else None
        if r['kind'] == 'date' and r['enabled'] and r['inside'] and alert and alert['delivery'] in {'sent', 'queued'}:
            r['state'] = 'sent' if alert['delivery'] == 'sent' else 'queued'
        result.append(r)
    return result


def validate(conn, c, company, original, *, confirmed=False):
    if c.kind not in {'price', 'date', 'research', 'response'}:
        raise a.AgentError('请选择到价、指定日期、研究变化或应对结论提醒。', 'UNSUPPORTED_WATCH_KIND')
    if c.kind == 'price':
        if c.threshold is None:
            raise a.AgentError('到什么价格提醒你？', 'MISSING_PRICE')
        if not confirmed:
            numbers = [float(n) for n in re.findall(r'(?<![A-Za-z\d.])\d+(?:\.\d+)?(?![A-Za-z\d.])', original.replace(',', ''))]
            if c.threshold not in numbers:
                raise a.AgentError('本条用户消息没有提醒价；“ok”或“A2”承接的条件必须先存为提醒草稿，再确认。不能补零或改小数点。',
                                   'PRICE_NOT_IN_CURRENT_MESSAGE', '已有草稿用confirm_watch；否则prepare_watch给出具体条件，只询问一次确认，不要换整数或小数反复重试。')
            if re.search(r'\d+(?:\.\d+)?\s*(?:/|或|或者)\s*\d', original):
                raise a.AgentError('你给了两个备选价格，请先确定用哪一个。', 'AMBIGUOUS_PRICE')
            up = bool(re.search(r'涨[到至破]|突破|高于|以上|不低于', original))
            down = bool(re.search(r'跌[到至破]|低于|以下|不高于', original))
            if (up and c.direction != 'above') or (down and c.direction != 'below'):
                raise a.AgentError('提醒方向与用户原话不一致，请核对涨到还是跌到。', 'PRICE_DIRECTION_MISMATCH')
        quote = assistant.freshest_price(conn, company['symbol'])
        if quote['price'] and not 0.2 <= c.threshold / quote['price'] <= 5:
            raise a.AgentError(f"提醒价 {c.threshold:g} 与库内价格 {quote['price']:g} 差距很大，请核对公司、币种和数值。", 'PRICE_OUTLIER')
        return c.direction, {}
    if c.kind == 'date':
        due = normalize_due(c.remind_at)
        if not confirmed:
            dates = re.findall(r'(?<!\d)(?:(\d{4})[-/年])?(\d{1,2})[-/月](\d{1,2})(?:日)?(?!\d)', original)
            if not any(int(y or now().year) == due.year and int(m) == due.month and int(d) == due.day for y, m, d in dates):
                raise a.AgentError('本条原话没有这个日期；请先提出带日期的提醒草稿，由用户确认。', 'DATE_NOT_IN_CURRENT_MESSAGE', 'prepare_watch，然后confirm_watch')
            clocks = re.findall(r'(?<!\d)(\d{1,2}):(\d{2})(?!\d)', original)
            if clocks:
                if (due.hour, due.minute) != tuple(map(int, clocks[0])):
                    raise a.AgentError('提醒时刻与用户原话不一致，请使用用户给出的时间。', 'REMINDER_TIME_MISMATCH')
            elif re.search(r'\d+点|上午|下午|晚上|中午|早上', original):
                raise a.AgentError('请先把这个时刻整理为明确的北京时间提醒草稿，由用户确认。', 'REMINDER_TIME_NEEDS_CONFIRMATION', 'prepare_watch，然后confirm_watch')
            elif (due.hour, due.minute) != (9, 0):
                raise a.AgentError('用户未给时刻时默认09:00；其他时刻需先提出提醒草稿供确认。', 'REMINDER_TIME_MISMATCH')
        return 'at:' + due.isoformat(), {'remind_at': due.isoformat()}
    if c.kind == 'response':
        from .response_report import build, watch_snapshot
        return 'below', watch_snapshot(build(conn, company['id']))
    return 'below', a._snapshot(conn, company)


def save(conn, c, company, original, *, confirmed=False):
    direction, snapshot = validate(conn, c, company, original, confirmed=confirmed)
    before = None
    if c.record_id:
        if not c.record_id.isdigit():
            raise a.AgentError('修改提醒请使用清单中的数字跟踪号。', 'INVALID_SUBSCRIPTION_ID')
        before = conn.execute('SELECT * FROM assistant_subscriptions WHERE id=? AND user_id=? AND company_id=?',
                              (int(c.record_id), a._scope(), company['id'])).fetchone()
        if not before:
            raise a.AgentError('找不到这家公司对应的提醒，先查看提醒清单。', 'WATCH_NOT_FOUND')
    collision = conn.execute('SELECT * FROM assistant_subscriptions WHERE user_id=? AND company_id=? AND kind=? AND direction=?',
                            (a._scope(), company['id'], c.kind, direction)).fetchone()
    if before and collision and before['id'] != collision['id']:
        raise a.AgentError('这个条件已有另一条提醒，请修改已有提醒，避免重复。', 'WATCH_EXISTS')
    before = before or collision
    unchanged = bool(before and before['kind'] == c.kind and before['direction'] == direction and before['threshold'] == c.threshold and before['enabled'])
    if unchanged:
        snapshot = a._load(before['snapshot'])
    if not unchanged and (not before or not before['enabled']):
        import os
        if os.getenv('STOCK_ASSISTANT_WEB_MODE') == 'cloud':
            count = conn.execute('SELECT COUNT(*) AS n FROM assistant_subscriptions WHERE user_id=? AND enabled=1', (a._scope(),)).fetchone()['n']
            if count >= 50:
                raise a.AgentError('当前已有50条跟踪，请先暂停不需要的提醒。', 'WATCH_LIMIT')
    reason = c.text.strip() or (before['reason'] if before else original[:1000])
    if before:
        if not unchanged:
            a._cancel_watch_alerts(conn, before['id'])
        conn.execute('''UPDATE assistant_subscriptions SET kind=?,direction=?,threshold=?,reason=?,snapshot=?,enabled=1,inside=?,updated_at=?
            WHERE id=? AND user_id=?''', (c.kind, direction, c.threshold, reason, a._json(snapshot), before['inside'] if unchanged else 0, now_iso(), before['id'], a._scope()))
        sid = before['id']
    else:
        sid = int(conn.execute('''INSERT INTO assistant_subscriptions(user_id,company_id,kind,threshold,direction,reason,snapshot,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?)''', (a._scope(), company['id'], c.kind, c.threshold, direction, reason, a._json(snapshot), now_iso(), now_iso())).lastrowid)
    import os
    running = assistant.watch_enabled() or os.getenv('STOCK_ASSISTANT_WEB_MODE') == 'cloud'
    label = f"北京时间{snapshot['remind_at'][:16].replace('T',' ')}的一次提醒；届时提示你查看，不代表财报已经发布。" if c.kind == 'date' else ''
    return {'message': '跟踪条件已保存。' + label + ('自动检查已开启。' if running else '自动检查尚未开启。'),
            'subscription_id': sid, 'company': company, 'kind': c.kind, 'threshold': c.threshold,
            'direction': direction, 'remind_at': snapshot.get('remind_at'), 'previous': dict(before) if before else None}


def execute(conn, e, company, action_id):
    c = e.command
    if c.operation == 'watch':
        return save(conn, c, company, e.original_text)
    if c.operation == 'prepare_watch':
        direction, snapshot = validate(conn, c, company, e.original_text, confirmed=True)
        label = (f"{'跌至' if direction == 'below' else '涨至'}{c.threshold:g}元提醒" if c.kind == 'price' else
                 f"{snapshot['remind_at'][:16].replace('T',' ')}（北京时间）提醒一次" if c.kind == 'date' else
                 {'research': '库内财报或公告有更新时提醒', 'response': '应对结论变化时提醒'}[c.kind])
        # One current proposal per company/kind/direction; reused option labels are superseded.
        old = conn.execute("SELECT id,payload FROM assistant_actions WHERE user_id=? AND session_key=? AND operation='prepare_watch' AND state='pending' AND id<>?", (a._scope(), e.session_key, action_id)).fetchall()
        for row in old:
            p = a._load(row['payload'])
            if (p.get('stock') == c.stock and p.get('kind') == c.kind and p.get('direction') == c.direction) or (c.choice and p.get('choice') == c.choice):
                conn.execute("UPDATE assistant_actions SET state='superseded',updated_at=? WHERE id=? AND user_id=?", (now_iso(), row['id'], a._scope()))
        return {'state': 'pending', 'company': company, 'choice': c.choice, 'condition': label,
                'message': f"待确认：{company['name']}，{label}。尚未启用。回复“确认 {action_id}”即可。",
                'expires_in_minutes': 15}
    old = a._action(conn, c.record_id, e.session_key)
    if old['operation'] != 'prepare_watch' or old['state'] != 'pending':
        raise a.AgentError('这条提醒草稿已完成、取消或被替代，请查看提醒清单。', 'DRAFT_NOT_PENDING')
    if old['created_at'] < (datetime.now() - timedelta(minutes=15)).isoformat():
        conn.execute("UPDATE assistant_actions SET state='expired' WHERE id=? AND user_id=?", (old['id'], a._scope()))
        return {'state': 'expired', 'message': '提醒草稿已过期，请重新提出条件。'}
    payload = a._load(old['payload'])
    original = e.original_text.strip().rstrip('。！!')
    explicit = bool(re.fullmatch(r'确认\s*' + re.escape(old['id']), original, re.I))
    selections = re.split(r'[、,，\s]+', original.upper())
    selected = bool(payload.get('choice') and all(re.fullmatch(r'[A-Z][1-9][0-9]{0,2}', x) for x in selections) and payload['choice'] in selections)
    pending = conn.execute("SELECT COUNT(*) AS n FROM assistant_actions WHERE user_id=? AND session_key=? AND operation='prepare_watch' AND state='pending' AND created_at>=?", (a._scope(), e.session_key, (datetime.now()-timedelta(minutes=15)).isoformat())).fetchone()['n']
    plain = original.lower() in {'ok', '好', '好的', '确认', '可以', '就这样'} and pending == 1
    if not (explicit or selected or plain) or payload.get('_message_id') == e.message_id:
        raise a.AgentError('请由用户在下一条消息确认具体提醒；有多条草稿时请给选项号或记录号。', 'WATCH_CONFIRMATION_REQUIRED')
    payload.pop('_message_id', None)
    proposal = a.Command.model_validate({**payload, 'operation': 'watch'})
    target = a._company(conn, old['company_id'])
    result = save(conn, proposal, target, e.original_text, confirmed=True)
    conn.execute("UPDATE assistant_actions SET state='done',result=?,updated_at=? WHERE id=? AND user_id=?", (a._json({**result, 'record_id': old['id'], 'state': 'done'}), now_iso(), old['id'], a._scope()))
    return result
