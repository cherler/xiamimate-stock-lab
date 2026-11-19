# 虾米看股 · 个人投资研究工作台

**把买入理由、证据和后续变化，放进同一份研究档案。**

面向 A 股个人投资者，将公司研究、财务估值、投资判断、持仓账本和复盘连接起来，持续核对：当初关注或买入它的理由，现在还成立吗？

[在线体验](https://cherler.github.io/xiamimate-stock-lab/) · [视频演示](https://cherler.github.io/xiamimate-stock-lab/promo/) · [本机部署](docs/DEVELOPMENT.md) · [文档导航](docs/README.md)

## 41 秒看一遍：你为什么买这只股？

[![虾米看股宣传视频：你为什么买这只股？点击播放](pages/public/promo/cover.png)](https://cherler.github.io/xiamimate-stock-lab/promo/)

[▶ 播放宣传视频](https://cherler.github.io/xiamimate-stock-lab/promo/) · 41 秒 · 1080p · 点击封面播放

视频展示录制时的完整服务。Pages 使用明确标注的虚构样例，功能与数据范围见下表；视频不构成投资建议。

## 围绕一次完整判断

| 环节 | 你可以做什么 |
| --- | --- |
| 看公司 | 将行情、财务、公告事件和估值放在公司档案中查看 |
| 写理由 | 记录投资逻辑、证据、反证条件与复核日期 |
| 做比较 | 使用产业链底图、行业对照、市场云图与方法库 |
| 看价格 | 通过三情景估值与假设试算，理解不同条件下的结果 |
| 留账本 | 记录买卖流水及当时理由，查看持仓、成本与集中度 |
| 持续复核 | 对照新事实与原判断，保留研究记录和修改历史 |

产品从个人投资者的真实处境出发，关注持仓、资金、时间与执行约束。市场和个人情绪如何进入判断仍需按实际任务验证，研发目标与已实现能力分别说明。

## 选一种使用方式

| | GitHub Pages | 本机或服务器部署 |
| --- | --- | --- |
| 工作台 | 原站前端与导航，浏览虚构公司样例 | 完整前端与 FastAPI 研究服务 |
| 行情与财务 | 演示走势和虚构财务，不是实时行情 | 按配置连接外部数据源，保留来源与截止时间 |
| 估值与笔记 | 三情景试算；个人笔记保存在浏览器，可导入导出 | 持久化研究库、判断、证据和持仓账本 |
| AI、定时任务、飞书 | 不在 Pages 运行 | 需要单独配置服务与凭据 |

Pages 的演示记录不对应真实证券或作者持仓。个人笔记不会自动上传或跨设备同步，复核日期也不会触发后台通知。完整能力与配置见 [功能说明](docs/FEATURES.md) 和 [Pages 说明](docs/PAGES.md)。

## 先在本地体验 Pages

需要 Node.js 22.13+。

```bash
git clone https://github.com/cherler/xiamimate-stock-lab.git
cd xiamimate-stock-lab
npm ci
npm run build:pages
npm run preview:pages
```

打开 <http://127.0.0.1:5228/xiamimate-stock-lab/>。若要运行真实数据与完整研究服务，按 [开发与部署指南](docs/DEVELOPMENT.md) 同时启动前端和 Python API；助手与飞书接入见 [助手说明](apps/assistant/README.md)。

## 项目结构

```text
apps/web/            React + TypeScript + ECharts 工作台
apps/api/            FastAPI 接口、研究库与数据服务
apps/assistant/      助手与消息渠道接入
pages/               Pages 数据适配、虚构样例与本地笔记
pages/public/promo/  宣传视频、封面与播放页
docs/                使用、开发、产品与实施文档
scripts/             数据、构建与检查工具
deploy/              服务部署配置
```

## 使用说明

- 项目用于研究记录、假设试算与复盘，不承诺投资收益，不自动执行证券交易。
- 完整部署请使用自己的数据与配置；源码不包含作者持仓、研究数据库、模型密钥或消息凭据。
- 代码采用 [AGPL-3.0](LICENSE)，第三方数据的使用以对应来源条款为准。
- [作者在线服务](https://xiamimate.com/stocks/)由个人维护，可能随时暂停或关闭，相关链接也可能失效。重要记录请定期导出。

## 虾米伙伴系列

[虾米跨境](https://github.com/cherler/xiamimate-crossborder) · [虾米看 AI](https://github.com/cherler/xiamimate-ai-atlas) · [虾米看股](https://github.com/cherler/xiamimate-stock-lab) · [虾米 CS 课堂](https://github.com/cherler/xiamimate-cs-lab) · [模型工坊](https://github.com/cherler/xiamimate-model-lab)

这些项目由个人持续维护。欢迎通过仓库 Issues 反馈问题、提出具体使用场景；觉得有用，也欢迎 Star 或分享。
