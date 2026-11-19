"""Generate public preview responses from an isolated, entirely fictional SQLite DB.

Never reads the developer's database or .env; no application lifespan/background jobs.
The checked-in result lets Pages use the real frontend without a running backend.
Run with .venv/bin/python scripts/build-pages-fixtures.py.
"""
import asyncio
import json
import math
import os
import socket
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))


async def generate(folder: Path):
    os.environ["STOCK_DB_BACKEND"] = "sqlite"
    os.environ["XIAMI_STOCK_DB"] = str(folder / "fictional-preview.db")
    os.environ["STOCK_ACCESS"] = "open"
    for key in list(os.environ):
        if key.startswith(("XM_", "PG_", "MINIMAX_", "FEISHU_", "STOCK_CLOUD_")):
            os.environ.pop(key)
    # No provider, model, gateway or credential configuration may be read.
    from stock_decision import llm
    llm.load_env = lambda: {key: '' for key in llm.ENV_KEYS}
    def no_network(*args, **kwargs):
        raise RuntimeError("Network is forbidden while generating public fixtures")
    socket.socket.connect = no_network
    import urllib.request
    urllib.request.OpenerDirector.open = no_network
    from stock_decision.database import initialize_database, database_path, connection
    assert database_path() == (folder / "fictional-preview.db").resolve()
    initialize_database()
    from stock_decision.main import app
    import httpx
    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver")
    as_of = "2026-11-18T15:00:00+08:00"
    source = "虚构演示数据，不对应真实证券"
    fixture_source = 'https://github.com/cherler/xiamimate-stock-lab/blob/main/scripts/build-pages-fixtures.py'
    companies = [
        ("海屿储能（示例）", "储能设备", 120, 8, 12, "收入增长后，要看回款有没有跟上。", "连续两期应收周转恶化。"),
        ("青岚算力（示例）", "数据中心", 80, 10, 16, "扩张兑现要同时看上架率和利息。", "上架慢于计划且利息支出继续增加。"),
        ("澄川制造（示例）", "工业制造", 300, 15, 5, "利润率不高，重点看周转与现金回收。", "库存与应收增长明显快于收入。"),
        ("云帆光联（示例）", "通信设备", 45, 5, 18, "订单增长之后，核对交付和客户集中度。", "大客户需求下调或存货明显增加。"),
        ("远峰电气（示例）", "电力设备", 65, 6, 9, "项目周期较长，重点跟踪现金流。", "项目交付延迟且预收款下降。"),
        ("北辰材料（示例）", "电子材料", 28, 4, 8, "新品放量必须体现为毛利和净利润。", "销量增长但单价与毛利率持续下降。"),
    ]
    async def create(path, body):
        r = await client.post('/api/v1' + path, json=body)
        if r.status_code >= 400: raise RuntimeError(f"Seed failed {path}: {r.text[:200]}")
        return r.json()
    ids = []
    for i, (name, industry, revenue, shares, margin, claim, counter) in enumerate(companies):
        symbol = f"99000{i+1}"
        company = await create('/companies', {"symbol":symbol,"name":name,"industry":industry,"description":source,"watch_group":"演示观察池","valuation_percentile":24+i*9,"roe_trend":"虚构样例，仅展示页面"})
        cid = company['id']; ids.append(cid)
        thesis = await create(f'/companies/{cid}/theses', {"claim":claim,"counter_condition":counter,"status":"watching" if i % 2 else "intact","next_review_trigger":"下一期演示财务数据","valuation_note":"所有金额与估值均为虚构"})
        await create(f'/companies/{cid}/evidences', {"thesis_id":thesis['id'],"source_name":source,"source_url":fixture_source,"excerpt":"虚构场景：收入增长，经营现金流仍需结合应收和存货核对。","polarity":"support","verification":"待核验"})
        await create(f'/companies/{cid}/events', {"thesis_id":thesis['id'],"category":"演示事件","title":"虚构季报更新：等待复核经营现金流","importance":"high" if i<2 else "medium","verification":"待核验"})
        days=[]; day=date(2026,11,18)
        while len(days)<400:
            if day.weekday()<5: days.append(day)
            day-=timedelta(days=1)
        prices=[]
        for n, day in enumerate(reversed(days)):
            close=round((18+i*5)*(1+n*.0008)+math.sin(n/19+i)*2+math.sin(n/4)*.35,2)
            prices.append((symbol,day.isoformat(),close,round(close*.995,2),round(close*1.018,2),round(close*.981,2),1000000+n*500,close*(1000000+n*500),round((close/prices[-1][2]-1)*100,2) if prices else 0,source,as_of))
        price=prices[-1][2]
        with connection() as conn:
            conn.executemany('INSERT INTO price_bars(symbol,trade_date,close,open_price,high,low,volume,amount,change_percent,source,refreshed_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)',prices)
            conn.execute('INSERT INTO market_snapshots(symbol,price,prev_close,change_percent,pe,pb,high_52w,low_52w,total_market_cap,market_timestamp,source,refreshed_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(symbol,price,prices[-2][2],prices[-1][8],15+i*4,1.5+i*.3,max(v[2] for v in prices),min(v[2] for v in prices),price*shares*1e8,as_of,source,as_of))
            for report, factor in [('2020-12-31',.45),('2021-12-31',.55),('2022-12-31',.65),('2023-12-31',.75),('2024-12-31',.85),('2025-12-31',1),('2025-03-31',.21),('2025-06-30',.46),('2025-09-30',.7),('2026-03-31',.24),('2026-06-30',.52),('2026-09-30',.82)]:
                rev=revenue*factor*1e8; profit=rev*margin/100; assets=revenue*1.3e8; equity=assets*.55
                conn.execute('INSERT INTO financial_periods(symbol,report_date,revenue,net_profit,operating_cash_flow,operating_cost,rnd_expense,capex,receivables,inventory,interest_bearing_debt,total_assets,total_liabilities,equity,debt_ratio,roe_estimate,source,refreshed_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(symbol,report,rev,profit,profit*(.65+i*.1),rev*.72,rev*.05,rev*.08,rev*.25,rev*.14,assets*.25,assets,assets-equity,equity,45,profit/equity*100,source,as_of))
            conn.execute('INSERT INTO market_universe(symbol,name,exchange,board,industry,price,change_percent,pe_ttm,pb,total_market_cap,report_date,revenue,revenue_growth,net_profit,net_profit_growth,roe,gross_margin,annual_roe,dividend_yield,sw_level1,sw_level2,price_source,price_as_of,fundamental_source,fundamental_as_of,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(symbol,name,'演示','虚构样例',industry,price,prices[-1][8],15+i*4,1.5+i*.3,price*shares*1e8,'2026-09-30',revenue*.82e8,14+i*2,revenue*.82e8*margin/100,10+i*3,12+i,28,12+i,1+i*.3,industry,industry,source,as_of,source,as_of,as_of))
            eps=revenue*.82*margin/100/shares
            conn.execute('UPDATE market_universe SET annual_gross_margin=?,eps=?,ocf_per_share=?,above_ma60=?,volume_days=?,new_high_level=?,turnover_rate=?,change_60d=?,ytd_change=?,rising_days=? WHERE symbol=?',(28,eps,eps*(.65+i*.1),int(price>sum(p[2] for p in prices[-60:])/60),i+1,2 if i%2 else 0,2+i*.2,(price/prices[-61][2]-1)*100,(price/next(p[2] for p in prices if p[1]>='2026-01-01')-1)*100,i+1,symbol))
            # Provider-keyed input for the shared valuation engine. Export metadata below
            # explicitly relabels these invented values; no provider is called.
            for n, point in enumerate(prices[::5]):
                for metric,value in [('pe_ttm',18+i*3+math.sin(n/8)*4),('pb',1.7+i*.2+math.sin(n/8)*.3)]:
                    conn.execute('INSERT INTO valuation_points(symbol,metric,point_date,value,source,refreshed_at) VALUES (?,?,?,?,?,?)',(symbol,metric,point[1],value,'StockSDK',as_of))
    portfolio = await create('/portfolios', {"name":"虚构演示组合","objective":"只用于展示持仓账本，不是真实投资记录","amount_mode":"full"})
    for i, cid in enumerate(ids[:3]):
        await create(f"/portfolios/{portfolio['id']}/trades", {"company_id":cid,"side":"buy","trade_date":"2026-09-01","shares":1000+i*500,"price":22+i*5,"fee":5,"rationale":"虚构样例：展示交易理由与仓位变化","expectation":"教学演示，没有真实成交"})
        r=await client.post(f'/api/v1/companies/{cid}/decision-card/enroll')
        if r.status_code>=400: print('Enroll skipped',r.status_code)
    await client.post('/api/v1/decision-loop/evaluate')
    # Seed themes from the product's public industry-chain templates.
    themes = (await client.get('/api/v1/industry-chains')).json()
    ai_theme = next(t for t in themes if t['name'] == 'AI 数据中心')
    ai_map = (await client.get(f"/api/v1/industry-chains/{ai_theme['id']}")).json()
    nodes={n['name']:n['id'] for stage in ai_map['stages'] for n in stage['nodes']}
    for cid,node in [(ids[1],'智能计算中心'),(ids[2],'AI服务器'),(ids[3],'高速网络'),(ids[4],'供配电与UPS')]:
        await create(f"/industry-chains/{ai_theme['id']}/positions",{'node_id':nodes[node],'company_id':cid,'role':'虚构位置演示','detail':source,'source_name':source,'source_url':fixture_source,'verification':'待补证'})
    static_paths = [
        '/dashboard','/companies','/companies/groups','/portfolios',f"/portfolios/{portfolio['id']}",'/decision-board','/decision-loop','/theses','/reviews/queue','/industries','/universe/summary','/screen/strategies','/screen/fields','/screen/ai-pick/options','/heatmap','/tasks','/methods','/settings','/inbox','/inbox/learning','/news','/news/feeds','/reports','/briefing','/documents','/industry-chains','/counter-hits','/market/lenses','/credits/state','/credits/estimates',
    ]
    result = {}
    for path in static_paths:
        r=await client.get('/api/v1'+path)
        if r.status_code==200: result['/api/v1'+path]=r.json()
        else: print('Not captured',path,r.status_code)
    for route in app.routes:
        path=getattr(route,'path','')
        if 'GET' not in getattr(route,'methods',[]) or not path.startswith('/api/v1/companies/{company_id}'): continue
        if path.count('{') != 1 or any(part in path for part in ['refresh','download','document','export']): continue
        for cid in ids:
            key=path.replace('{company_id}',str(cid))
            try:
                r=await client.get(key)
                if r.status_code==200: result[key]=r.json()
                else: print('Not captured',key,r.status_code)
            except Exception as e: print('Skipped',key,type(e).__name__)
    for theme in themes if isinstance(themes,list) else []:
        key=f"/api/v1/industry-chains/{theme['id']}"
        r=await client.get(key)
        if r.status_code==200:result[key]=r.json()
    for scope in ['all','watched']:
        for metric in ['roe','change_percent','change_5d','change_20d','ytd_change','turnover_rate','abs_change','attention_index','capital_flow','pe_ttm','pb','revenue_growth','net_profit_growth','dividend_yield']:
            key=f'/api/v1/heatmap?metric={metric}&scope={scope}'
            r=await client.get(key)
            if r.status_code==200:result[key]=r.json()
    for item in result['/api/v1/screen/strategies']:
        key=f"/api/v1/screen/run?strategy={item['key']}"
        r=await client.post(key)
        if r.status_code==200:result[key]=r.json()
        else: result[key]={'preview_error':r.json().get('detail','样例数据不支持这组筛选条件')}
    for _,industry,*_ in companies:
        from urllib.parse import urlencode
        key='/api/v1/industries/comparison?'+urlencode({'industry':industry})
        r=await client.get(key)
        if r.status_code==200:result[key]=r.json()
    r=await client.get('/api/v1/response-reports?company_ids='+','.join(map(str,ids)))
    if r.status_code==200:result['/api/v1/response-reports']=r.json()
    result['/api/v1/market/fund-flow']={'source':source,'as_of':as_of,'unit':'亿元','points':[],'boundary':'演示数据没有资金流，不能据此推断真实资金行为。'}
    # These capabilities are explicitly absent; never export environment-derived identities.
    result['/api/v1/access']={'mode':'preview','is_owner':False,'is_guest':False,'can_write':False,'owner_configured':False,'follows_console':False}
    result['/api/v1/assistant/web/messages']=[]
    result['/api/v1/assistant/web/status']={'mode':'guide','ready':False,'configured':False,'feishu_bound':False,'message':'Pages 不运行助手；请使用完整在线服务或本机部署。','guide':[{'title':'Pages 只展示界面，不运行助手','done':False,'text':'AI 研究、飞书连接与自动提醒需要运行完整服务。'}],'settings_url':'https://github.com/cherler/xiamimate-stock-lab/blob/main/apps/assistant/README.md'}
    result['/api/v1/dashboard']['demo']=True
    result['/api/v1/dashboard']['viewer_is_guest']=False
    result['/api/v1/dashboard']['as_of']=as_of
    result['/api/v1/dashboard']['data_health']='虚构演示数据，无行情同步'
    def label_fiction(value):
        if isinstance(value,dict):
            return {k:(source if k in ['source','price_source','fundamental_source','market_source'] and isinstance(v,str) else '虚构演示' if k=='exchange' else True if k=='is_sample' else label_fiction(v)) for k,v in value.items()}
        if isinstance(value,list):return [label_fiction(v) for v in value]
        return value
    result=label_fiction(result)
    for key,value in result.items():
        if key.startswith('/api/v1/heatmap') and isinstance(value,dict):value['scope_label']='六家虚构样例'
    output=ROOT/'pages/src/fixtures.json'
    output.write_text(json.dumps({'fictional':True,'as_of':as_of,'responses':result},ensure_ascii=False,separators=(',',':')))
    print(f'Captured {len(result)} responses, {len(ids)} fictional companies; {output.stat().st_size} bytes')
    await client.aclose()


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='xiami-pages-fictional-') as directory:
        asyncio.run(generate(Path(directory)))
