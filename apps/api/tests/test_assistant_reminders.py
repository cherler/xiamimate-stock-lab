import hashlib
import hmac
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from stock_decision import assistant_agent as agent, assistant_watches as watches, access
from stock_decision import assistant_cli as cli
from stock_decision.database import connection
from test_assistant_agent import company, run, message, quote
from test_idor import client


def test_integer_price_and_actionable_rejection():
    company('宁德时代', '300750'); quote('300750', 297)
    with pytest.raises(agent.AgentError) as err:
        run('watch', original='ok', stock='宁德时代', kind='price', threshold=285)
    assert err.value.detail['code'] == 'PRICE_NOT_IN_CURRENT_MESSAGE'
    assert err.value.detail['retryable'] is False
    saved=run('watch', original='宁德时代跌破285提醒我', stock='宁德时代', kind='price', threshold=285)
    assert saved['threshold']==285
    with pytest.raises(agent.AgentError,match='备选'):
        run('watch', mid='alternatives', original='285 / 280', stock='宁德时代',kind='price',threshold=285)
    with pytest.raises(agent.AgentError,match='方向'):
        run('watch', mid='wrong-way', original='涨到285', stock='宁德时代',kind='price',threshold=285)


def test_proposal_then_ok_confirms_immutable_draft_once():
    company();quote('601138',32)
    draft=run('prepare_watch',stock='工业富联',kind='price',threshold=30,choice='A2')
    assert run('list_watches')['subscriptions']==[]
    with pytest.raises(agent.AgentError,match='下一条'):
        run('confirm_watch',original='ok',record_id=draft['record_id'])
    result=run('confirm_watch',original='ok',mid='m2',record_id=draft['record_id'],threshold=999)
    assert result['threshold']==30
    assert run('confirm_watch',original='ok',mid='m2',record_id=draft['record_id'])['replayed']
    assert len(run('list_watches')['subscriptions'])==1
    replay=run('prepare_watch',stock='工业富联',kind='price',threshold=30,choice='A2')
    assert replay['state']=='done' and replay['subscription_id']==result['subscription_id']


def test_multiple_options_can_be_selected_together():
    company();quote('601138',32)
    price=run('prepare_watch',stock='工业富联',kind='price',threshold=30,choice='A2')
    dated=run('prepare_watch',stock='工业富联',kind='date',remind_at='2099-10-20',choice='A3')
    with pytest.raises(agent.AgentError,match='多条'):
        run('confirm_watch',original='ok',mid='m2',record_id=price['record_id'])
    for draft in (price,dated):
        run('confirm_watch',original='A3、A2',mid='m3',record_id=draft['record_id'])
    assert len(run('list_watches')['subscriptions'])==2


def test_fill_and_watch_proposals_have_independent_lifecycles():
    company()
    draft=run('prepare_watch',stock='工业富联',kind='date',remind_at='2099-10-20')
    run('prepare_fill',mid='fill',stock='工业富联',price=30,shares=100)
    with pytest.raises(agent.AgentError) as error:
        run('confirm',original='确认',mid='wrong-confirm',record_id=draft['record_id'])
    assert error.value.detail['code']=='WRONG_CONFIRMATION_TOOL'
    saved=run('confirm_watch',original='ok',mid='right-confirm',record_id=draft['record_id'])
    assert saved['kind']=='date'
    draft=run('prepare_watch',mid='other-date',stock='工业富联',kind='date',remind_at='2099-10-21')
    assert '提醒草稿' in run('cancel',mid='cancel',record_id=draft['record_id'])['message']


def test_confirmation_session_scope_cancel_and_expiry():
    company()
    draft=run('prepare_watch',stock='工业富联',kind='date',remind_at='2099-10-20')
    e=message('confirm_watch',original='ok',mid='m2',record_id=draft['record_id']);e.session_key='other'
    with pytest.raises(agent.AgentError):agent.dispatch(e)
    token=access.set_scope('stranger')
    try:
        assert run('list_watches')['subscriptions']==[]
        with pytest.raises(agent.AgentError):run('confirm_watch',original='ok',mid='m2',record_id=draft['record_id'])
    finally:access.reset_scope(token)
    run('cancel',mid='m2',record_id=draft['record_id'])
    with pytest.raises(agent.AgentError):run('confirm_watch',original='ok',mid='m3',record_id=draft['record_id'])
    draft=run('prepare_watch',mid='m4',stock='工业富联',kind='date',remind_at='2099-10-20')
    with connection() as conn:conn.execute("UPDATE assistant_actions SET created_at='2000-01-01' WHERE id=?",(draft['record_id'],))
    assert run('confirm_watch',original='ok',mid='m5',record_id=draft['record_id'])['state']=='expired'


def test_date_weekend_once_catchup_and_delivery(monkeypatch):
    company()
    now=datetime(2026,10,10,8,0,tzinfo=ZoneInfo('Asia/Shanghai'))
    monkeypatch.setattr(watches,'now',lambda:now)
    saved=run('watch',original='10-10三季度发财报提醒我',stock='工业富联',kind='date',remind_at='10-10',text='看三季报')
    assert saved['remind_at']=='2026-10-10T09:00:00+08:00'
    assert agent.scan_subscriptions()==[]
    now+=timedelta(hours=2)
    alerts=agent.scan_subscriptions()
    assert len(alerts)==1 and '补发' in alerts[0]['message'] and '不代表财报' in alerts[0]['message']
    assert agent.scan_subscriptions()==[]
    row=run('list_watches')['subscriptions'][0]
    assert row['id']==saved['subscription_id'] and row['last_delivery']['delivery']=='pending'
    with connection() as conn:conn.execute("UPDATE assistant_alerts SET delivery='sent' WHERE id=?",(alerts[0]['id'],))
    assert run('list_watches')['subscriptions'][0]['state']=='sent'


def test_date_edit_cancels_old_outbox_and_past_resume_rejected(monkeypatch):
    company()
    now=datetime(2026,10,10,8,0,tzinfo=ZoneInfo('Asia/Shanghai'))
    monkeypatch.setattr(watches,'now',lambda:now)
    saved=run('watch',original='10-10提醒我',stock='工业富联',kind='date',remind_at='10-10')
    now+=timedelta(hours=2);agent.scan_subscriptions()
    run('pause_watch',mid='pause',record_id=str(saved['subscription_id']))
    with pytest.raises(agent.AgentError,match='过去'):
        run('resume_watch',mid='resume',record_id=str(saved['subscription_id']))
    edited=run('watch',mid='edit',original='改到10-20',stock='工业富联',record_id=str(saved['subscription_id']),kind='date',remind_at='10-20')
    assert edited['subscription_id']==saved['subscription_id']
    with connection() as conn:assert conn.execute('SELECT delivery FROM assistant_alerts').fetchone()['delivery']=='skipped'
    assert agent.scan_subscriptions()==[]


def test_multiple_dates_and_foreign_reminder_isolation(client):
    company()
    one=run('watch',original='2099-10-20',stock='工业富联',kind='date',remind_at='2099-10-20')
    run('watch',original='2099-10-21',stock='工业富联',kind='date',remind_at='2099-10-21')
    assert len(client.get('/api/v1/assistant/watches').json()['subscriptions'])==2
    client.as_user('other')
    assert client.get('/api/v1/assistant/watches').json()['subscriptions']==[]
    token=access.set_scope('other')
    try:
        company('别人的公司','000001')
        with pytest.raises(agent.AgentError):
            run('watch',mid='attack',original='2099-10-22',stock='别人的公司',kind='date',remind_at='2099-10-22',record_id=str(one['subscription_id']))
    finally:access.reset_scope(token)


def test_cloud_limit_covers_confirmation_but_allows_edit(monkeypatch):
    company();monkeypatch.setenv('STOCK_ASSISTANT_WEB_MODE','cloud')
    from datetime import date
    start=date(2099,1,1);first=None
    for i in range(50):
        day=(start+timedelta(days=i)).isoformat()
        item=run('watch',mid=day,original=day,stock='工业富联',kind='date',remind_at=day)
        first=first or item
    draft=run('prepare_watch',mid='draft',stock='工业富联',kind='date',remind_at='2099-12-31')
    with pytest.raises(agent.AgentError,match='50'):
        run('confirm_watch',mid='confirm',original='ok',record_id=draft['record_id'])
    assert run('watch',mid='edit',original='2099-12-30',stock='工业富联',kind='date',remind_at='2099-12-30',record_id=str(first['subscription_id']))['subscription_id']==first['subscription_id']


def test_cli_signed_integer_input_and_remote_guard(monkeypatch):
    args=cli.parser().parse_args(['watch','--stock','宁德时代','--below','285'])
    req=cli.request_for(args,{'secret':'test'});body=json.loads(req.data)
    assert body['command']['threshold']==285 and '285' in body['original_text']
    signature=req.headers['X-stock-signature']
    assert hmac.compare_digest(signature,hmac.new(b'test',req.data,hashlib.sha256).hexdigest())
    monkeypatch.setattr(agent,'bridge_config',lambda:{'secret':'test'})
    assert agent.verify_request(req.data,signature).channel=='local-cli'
    args.api='https://example.com'
    with pytest.raises(ValueError,match='外部'):cli.request_for(args,{'secret':'test'})


def test_structured_errors_and_capabilities(client,monkeypatch):
    company();monkeypatch.setattr(agent,'bridge_config',lambda:{'secret':'test','channel':'feishu','chat_id':'private','sender_ids':['owner']})
    e=message('watch',original='ok',stock='工业富联',kind='price',threshold=30);raw=e.model_dump_json().encode()
    r=client.post('/api/v1/assistant/command',content=raw,headers={'X-Stock-Signature':hmac.new(b'test',raw,hashlib.sha256).hexdigest()})
    assert r.status_code==422 and r.json()['detail']['code']=='PRICE_NOT_IN_CURRENT_MESSAGE'
    assert 'date' in client.get('/api/v1/assistant/capabilities').json()['watch_kinds']


def test_date_year_time_cannot_be_silently_changed(monkeypatch):
    company()
    monkeypatch.setattr(watches,'now',lambda:datetime(2026,10,11,8,tzinfo=ZoneInfo('Asia/Shanghai')))
    for raw,due in [('2027-10-20','2026-10-20'), ('10-20 15:00','2026-10-20 09:00'), ('10-20','2026-10-20 18:00')]:
        with pytest.raises(agent.AgentError):run('watch',original=raw,stock='工业富联',kind='date',remind_at=due)
    saved=run('watch',original='10-20 15:00提醒我',stock='工业富联',kind='date',remind_at='10-20 15:00')
    assert saved['remind_at']=='2026-10-20T15:00:00+08:00'


def test_replaced_option_and_nonaffirmative_text_cannot_confirm():
    company()
    old=run('prepare_watch',stock='工业富联',kind='price',threshold=30,choice='A2')
    new=run('prepare_watch',mid='m2',stock='工业富联',kind='price',threshold=31,choice='A2')
    with pytest.raises(agent.AgentError):run('confirm_watch',original='A2',mid='m3',record_id=old['record_id'])
    with pytest.raises(agent.AgentError):run('confirm_watch',original='不要确认A2',mid='m4',record_id=new['record_id'])
    assert run('confirm_watch',original='A2',mid='m5',record_id=new['record_id'])['threshold']==31


def test_bridge_and_api_advertise_same_command_contract():
    import ast
    from pathlib import Path
    module=ast.parse((Path(__file__).resolve().parents[2]/'assistant/bridge/stock_assistant_bridge.py').read_text())
    cls=next(n for n in module.body if isinstance(n,ast.ClassDef) and n.name=='StockAssistantTool')
    assignment=next(n for n in cls.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='parameters' for t in n.targets))
    properties=ast.literal_eval(assignment.value)['properties']
    api=agent.Command.model_json_schema()['properties']
    assert set(properties)==set(api)
    assert set(properties['operation']['enum'])==set(api['operation']['enum'])
    assert set(properties['kind']['enum'])==set(api['kind']['enum'])
