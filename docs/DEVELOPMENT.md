# 开发与部署指南

完整服务的前端、API、数据同步与部署说明。静态体验另见 [Pages 说明](PAGES.md)。返回 [项目首页](../README.md)。

## 快速开始

### 前端

```bash
git clone https://github.com/cherler/xiamimate-stock-lab.git
cd xiamimate-stock-lab
npm ci
npm run dev:standalone
```

独立部署打开 `http://127.0.0.1:5217/`，下面的 API 也需要启动。`dev:standalone` 强制使用根路径，不依赖虾米伙伴的主站网关；若 API 未启动，会明确提示连接失败，不会展示伪造数据。作者自己的主站集成环境仍使用 `http://127.0.0.1:3000/stocks/`，原 `npm run dev` 启动方式保留。

### API

需要 Python 3.11+ 和 Node.js 22+。另开终端，在仓库根目录运行：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
python -m uvicorn stock_decision.main:app --reload --app-dir apps/api --host 127.0.0.1 --port 8108
```

Windows 使用 `.venv\Scripts\Activate.ps1` 激活虚拟环境。接口文档位于 `http://127.0.0.1:8108/docs`。不配置模型即可先用非 AI 功能；模型、行情与财报接口分别依赖自己的配置和外部网络。默认本地模式没有公网身份认证，只监听本机；对外部署请先配置 `STOCK_ACCESS`、账户隔离及 HTTPS，参照 `.env.production.example`，不要直接暴露开放模式。

首次启动 API 会在 `var/stock_decision.db` 建立本地数据库。若档案为空，系统通过 [StockSDK](https://stock-sdk.linkdiary.cn/guide/introduction) 同步 3 只真实 A 股作为起始研究池：代码、名称、价格、涨跌幅、PE、PB、52 周区间、时间和来源均来自 SDK，不使用虚构行情或公司资料。这个数据库仅保存在本机，已在版本控制中忽略。

在总览点击“同步实时行情”，或调用以下接口，可以刷新所有已关注公司的行情快照：

```bash
curl -X POST http://localhost:8108/api/v1/market/refresh
```

同步由服务端调用 `stock-sdk`，前端只读取本地快照。StockSDK 需要 Node.js 18+；本项目已将它锁定为前端工作区的依赖。

财务数据由服务端通过 [AKShare 的新浪财经定期报告接口](https://akshare.akfamily.xyz/data/stock/stock.html) 同步，读取利润表、现金流量表和资产负债表的原始报告期数值。年报 ROE 是以归母净利润除以平均归母权益得到的估算值，只在年度报告显示；非年报不会被伪装成年度 ROE。可在公司档案点击“同步财务数据”，或调用：

```bash
curl -X POST http://localhost:8108/api/v1/companies/1/financials/refresh
```

财务指标里的派生值都写明口径：毛利率取 (营收 − 营业成本) / 营收，现金含量取 经营现金流 / 归母净利润，自由现金流按 经营现金流 − 购建长期资产支付的现金 估算，周转天数按报告期天数折算；TTM 为"本期累计 + 上年年报 − 上年同期累计"。非年报不会与年报直接比较金额和周转天数，来源没有的科目显示为空而不是 0，并在提示区列出缺口。

行业、投资逻辑、公告和证据字段不会用示例内容填充；未接入时会明确显示为空或待补充。

新建公司时，在“公司档案”输入 6 位 A 股代码并点击“校验代码”。系统只会在 StockSDK 返回真实名称和行情后创建档案；行业、研究缘起和投资逻辑依然由你补充与确认。也可用以下接口进行校验：

```bash
curl 'http://localhost:8108/api/v1/quotes/resolve?symbol=600519'
curl http://localhost:8108/api/v1/data-providers
```

## 挂载到虾米伙伴（本地验证）

线上是单域名 + 路径分流，本机默认各跑各的端口——这个差异只有部署后才会暴露，
而暴露方式通常是「点进去一片空白」。`scripts/local-gateway.py` 把线上 Caddy 的规则原样搬到本机，
让「从虾米伙伴点进虾米看股」这条链路在推服务器之前就能走一遍。

```bash
# 1. 两边都按生产参数构建
VITE_BASE=/stocks/ npm run build
cd ../xiamimate-tools-frontend && NEXT_PUBLIC_API_BASE="" NEXT_PUBLIC_AI_ENABLED=1 npm run build && cd -

# 2. 后端照常跑在 8108
uvicorn stock_decision.main:app --reload --app-dir apps/api --port 8108

# 3. 起本地网关，规则与 deploy/caddy-snippet.conf 一一对应
python3 scripts/local-gateway.py --stocks apps/web/dist --main ../xiamimate-tools-frontend/out
# → http://127.0.0.1:8090/ 是可选的隔离网关验证入口；日常从主站
#   http://127.0.0.1:3000/stocks 进入，不要把 5217 当作用户入口。
```

**接口前缀不能用 `/api`**：线上 `/api/*` 已被主站的 AI 闸口占用（Caddy 转 8200）。
入口用 `handle_path /stocks-api/*` 剥掉前缀再转发到 8108，后端看到的仍是 `/api/v1/...`，一行不用改。

前端靠**挂载路径**而不是主机名判断部署形态（`apps/web/src/config.ts`）——
用主机名会把「在本机跑生产形态」误判成开发环境，接口打到主站后端去，页面就是白的。

## 上线之前跑什么

```bash
bash scripts/release-check.sh        # 门禁：两个数据库各跑一遍测试、前端、构建+首屏预算、依赖漏洞
                                     # --fast 可跳过 SQLite 那一遍（赶时间时才用）

# 部署形态的冒烟：真实的 /stocks/ 路径 + 真实浏览器
PLAYWRIGHT_PATH=<某处的 playwright/index.mjs> node scripts/smoke.mjs --base http://127.0.0.1:8092

ssh xiamimate-app-01 'bash /srv/xiamimate/xiamimate-stock-lab/deploy/deploy.sh'
```

**为什么冒烟单独一支。** 单元测试再厚也绕不过两样东西：部署形态（挂在 `/stocks/`
子路径下、接口前缀是 `/stocks-api`）和浏览器。已经因此漏过两次——三个下载链接
裸写 `/api/…`（测试只看 `fetch(`），以及熔断抛的 `CreditsError` 被接口层的
`except RuntimeError` 改写成 503（单测直接调 `llm.reserve()`，走不到那一层）。

`scripts/smoke.mjs` 里写死了一条铁律：**找不到目标 = 失败，不是跳过**。
第一版把"页面上没有可删的策略"写成跳过，于是整支脚本打了绿色的 ✓，
而真正要验的那一步一次都没跑。

## 服务器上跑在哪个账号下

`deploy/harden-service.sh` 一次性把后端从 root 降到 `xiamimate` 系统账号
（幂等、可重复跑）。**改 unit 里的 `User=` 之前必须先跑它**：用户不存在时
systemd 直接拒绝启动，那是一次实打实的停服。回滚写在脚本顶部。
