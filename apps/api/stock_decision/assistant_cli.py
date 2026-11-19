"""Local operator CLI. Bot shell access stays disabled; writes use the signed API."""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import sys
import time
import uuid
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError


def parser():
    p = argparse.ArgumentParser(prog='xiami-stock', description='虾米看股本机工具；默认JSON输出，不启动模型。')
    p.add_argument('--api', default='http://127.0.0.1:8108')
    sub = p.add_subparsers(dest='verb', required=True)
    for name in ('capabilities', 'status', 'stocks', 'doctor'):
        sub.add_parser(name)
    listing = sub.add_parser('watches'); listing.add_argument('--stock', default='')
    for name in ('context', 'compare'):
        q=sub.add_parser(name); q.add_argument('--stock', required=True)
    for name in ('pause', 'resume', 'cancel'):
        q=sub.add_parser(name); q.add_argument('id')
    q=sub.add_parser('watch'); q.add_argument('--stock', required=True)
    group=q.add_mutually_exclusive_group(required=True)
    group.add_argument('--below', type=float); group.add_argument('--above', type=float)
    group.add_argument('--at', help='日期或日期时间，北京时间，默认09:00')
    group.add_argument('--research', action='store_true'); group.add_argument('--response', action='store_true')
    q.add_argument('--reason', default=''); q.add_argument('--id', default='', help='修改清单中的数字跟踪号')
    q=sub.add_parser('note'); q.add_argument('--stock', required=True); q.add_argument('text')
    q=sub.add_parser('correct'); q.add_argument('id'); q.add_argument('text')
    q=sub.add_parser('undo'); q.add_argument('id')
    q=sub.add_parser('resolve'); q.add_argument('stock')
    q=sub.add_parser('research'); q.add_argument('--stock',required=True)
    q.add_argument('--section',default='financials',choices=['financials','theses','valuation','reports','response'])
    q=sub.add_parser('check'); q.add_argument('--stock',required=True); q.add_argument('--price',type=float)
    q=sub.add_parser('preferences'); q.add_argument('--text', default='')
    q=sub.add_parser('action', help='高级入口，使用capabilities所列的统一动作；不会绕过确认')
    q.add_argument('--json', required=True, dest='command_json'); q.add_argument('--original', required=True)
    return p


def command_for(args):
    v=args.verb
    if v == 'watch':
        c={'operation':'watch', 'stock':args.stock, 'text':args.reason, 'record_id':args.id}
        if args.at:
            c.update(kind='date', remind_at=args.at); original=f'{args.stock} {args.at} 提醒我 {args.reason}'
        elif args.research or args.response:
            c.update(kind='research' if args.research else 'response'); original=f'跟踪{args.stock} {args.reason}'
        else:
            value=args.below if args.below is not None else args.above
            c.update(kind='price', threshold=value, direction='below' if args.below is not None else 'above')
            original=f"{args.stock} {'跌至' if args.below is not None else '涨至'}{value:g}提醒我 {args.reason}"
        return c, original
    if v in {'pause','resume','cancel','undo'}:
        return {'operation':{'pause':'pause_watch','resume':'resume_watch','cancel':'cancel','undo':'undo'}[v], 'record_id':args.id}, f'{v} {args.id}'
    if v=='correct':
        return {'operation':'correct','record_id':args.id,'text':args.text},args.text
    if v in {'context','compare'}:
        return {'operation':v, 'stock':args.stock}, f'{v} {args.stock}'
    if v=='note':
        return {'operation':'remember','stock':args.stock,'text':args.text}, args.text
    if v=='preferences':
        return {'operation':'preferences','text':args.text}, args.text or '查看偏好'
    return json.loads(args.command_json), args.original


def request_for(args, config=None):
    url=urlparse(args.api)
    if url.scheme != 'http' or url.hostname not in {'localhost','127.0.0.1','::1'} or url.username or url.password or url.query or url.fragment or url.path not in {'','/'}:
        raise ValueError('这个CLI只允许连接本机HTTP接口，不会把本机签名发送到外部地址。')
    reads={'capabilities':'capabilities','status':'status','stocks':'my-stocks','watches':'watches?'+urlencode({'stock':getattr(args,'stock','')})}
    if args.verb in reads:
        return Request(args.api.rstrip('/')+'/api/v1/assistant/'+reads[args.verb])
    if args.verb in {'resolve','research','check'}:
        return Request(args.api.rstrip('/')+'/api/v1/assistant/resolve?'+urlencode({'q':args.stock}))
    if args.verb == 'doctor':
        return Request(args.api.rstrip('/')+'/health')
    if config is None:
        config=json.loads((Path.home()/'.nanobot/stock-assistant-bridge.json').read_text())
    command, original=command_for(args)
    envelope={'command':command,'original_text':original,'channel':'local-cli','chat_id':'terminal',
              'sender_id':'local-owner','session_key':'local-cli','message_id':str(uuid.uuid4()),'sent_at':int(time.time())}
    raw=json.dumps(envelope,ensure_ascii=False).encode()
    signature=hmac.new(config['secret'].encode(), raw, hashlib.sha256).hexdigest()
    return Request(args.api.rstrip('/')+'/api/v1/assistant/command',data=raw,method='POST',headers={'Content-Type':'application/json','X-Stock-Signature':signature})


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HTTPError(req.full_url, code, 'CLI refuses redirects', headers, fp)


def fetch(req):
    with build_opener(NoRedirect).open(req, timeout=35) as response:
        return json.loads(response.read())


def main(argv=None):
    args=parser().parse_args(argv)
    try:
        req=request_for(args)
        result=fetch(req)
        if args.verb in {'research','check'}:
            if len(result)!=1 or not result[0].get('company_id'):
                raise ValueError('公司没有唯一匹配，请先用resolve查公司名或代码。')
            cid=result[0]['company_id']
            tail=(f'research/{cid}?'+urlencode({'section':args.section}) if args.verb=='research' else
                  f'check/{cid}'+('?' + urlencode({'price':args.price}) if args.price is not None else ''))
            result=fetch(Request(args.api.rstrip('/')+'/api/v1/assistant/'+tail))
        elif args.verb=='doctor':
            base=args.api.rstrip('/')+'/api/v1/assistant/'
            result={'health':result,'capabilities':fetch(Request(base+'capabilities')),'reminder_checks':fetch(Request(base+'status'))}
        print(json.dumps(result,ensure_ascii=False,indent=2)); return 0
    except HTTPError as exc:
        try: detail=json.loads(exc.read()).get('detail', '请求失败')
        except ValueError: detail='请求失败'
        print(json.dumps({'ok':False,'status':exc.code,'error':detail},ensure_ascii=False),file=sys.stderr); return 2
    except (OSError, ValueError, KeyError, URLError) as exc:
        message='本机连接配置或服务不可用，请检查API和助手安装状态。' if isinstance(exc,(OSError,KeyError)) else str(exc)
        print(json.dumps({'ok':False,'error':message},ensure_ascii=False),file=sys.stderr); return 2


if __name__=='__main__':
    raise SystemExit(main())
