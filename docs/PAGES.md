# GitHub Pages：静态研究入口

访问：<https://cherler.github.io/xiamimate-stock-lab/>

完整源码、后端和助手都在本仓库。`pages/` 是同一项目的独立静态入口，不另建简化版仓库，也不把完整工作台的服务端接口伪装成已经可用。

## 当前可以使用

| 功能 | 数据与保存方式 |
|---|---|
| 三组公司研究样例、价格图、事实与反证 | 全部为代码中手写的虚构教学样例，不对应真实证券 |
| 三情景估值 | 复用 `apps/web/src/lib/valuation.ts`；输入只保留在当前页面 |
| 个人判断笔记 | 浏览器 localStorage，支持保存、修改、删除与 JSON 导入导出 |
| 安装与飞书说明 | 页面内的使用指南和完整仓库文档 |

实时行情、财报查询、AI 研究、定时任务、飞书机器人、数据库与账户需要运行完整服务。Pages 不连接作者的后台，不带登录 Cookie，也不调用第三方行情接口；外部链接仅在用户点击后访问。

笔记不自动上传或跨设备同步；复核日期不会产生通知。请定期导出，清理浏览器网站数据会删除本地笔记。GitHub Pages 的同一域名可能承载作者的其他项目，本地存储不是密码保险箱，不应保存模型密钥、账户凭据或敏感持仓信息。导入只接受本站版本 1 格式，按编号合并且不覆盖已有笔记；格式不对时保留原数据。JSON 是本页面备份格式，不是完整服务的数据库备份。

## 本机预览

需要 Node.js 22.13+，在仓库根目录：

```bash
npm ci
npm run test:pages
npm run build:pages
npm run preview:pages
```

打开 `http://127.0.0.1:5228/xiamimate-stock-lab/`。开发时可使用 `npm run dev:pages`。构建输出为 `dist/pages/`，不会覆盖 `apps/web/dist/`。所有前端路由使用 `#research`、`#valuation`、`#notebook` 和 `#guide`，刷新不需要服务器重写规则。

## 在自己的 GitHub 上部署

1. Fork 完整仓库；在 Settings → Pages → Build and deployment 中选择 **GitHub Actions**。
2. 进入 Actions，启用工作流，选择 **Publish GitHub Pages** → **Run workflow**。
3. 等待 build 和 deploy 完成，打开该部署的地址。

工作流读取 GitHub Pages 的 `base_path`，因此 Fork 后更换仓库名称也不必修改源码。后续 main 分支中的静态入口或依赖变更会触发自动发布。只上传 `dist/pages/`，不上传完整仓库目录，不使用模型密钥或飞书配置。

项目站点路径默认 `/xiamimate-stock-lab/`。自定义本地路径可在构建时传入 `PAGES_BASE=/你的路径/`；独立域名用 `/`。`PAGES_BASE` 只是路径，不含任何秘密。

## 完整服务

查看根目录 [README](../README.md) 的独立启动说明，及 [助手安装文档](../apps/assistant/README.md)。完整前端和 API 需要一起启动，Pages 不能代替 API。

[作者在线服务](https://xiamimate.com/stocks/)由个人维护，可能随时暂停或关闭，链接也可能失效。静态 Pages 与该服务独立发布，不保证任何托管服务永久可用。
