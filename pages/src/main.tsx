import { StrictMode, useEffect, useState, type FormEvent } from "react";
import { createRoot } from "react-dom/client";
import { BookOpen, Calculator, NotebookPen, ArrowUpRight, Download, Upload, Github, Menu, X, Check, Search, ChevronRight, CircleHelp } from "lucide-react";
import { valueOf, inYi } from "../../apps/web/src/lib/valuation";
import { samples } from "./samples";
import { MAX_NOTES, STORAGE_KEY, parseNotebook, serializeNotebook, mergeNotes, type Note } from "./notebook";
import "./style.css";

const REPO = "https://github.com/cherler/xiamimate-stock-lab";
const routes = [
  { id: "research", label: "研究样例", icon: BookOpen },
  { id: "valuation", label: "估值试算", icon: Calculator },
  { id: "notebook", label: "我的笔记", icon: NotebookPen },
  { id: "guide", label: "使用与部署", icon: CircleHelp },
] as const;
type Route = typeof routes[number]["id"];
function initialRoute(): Route {
  const id = window.location.hash.slice(1);
  return routes.find(r => r.id === id)?.id ?? "research";
}
function loadNotes(): { notes: Note[]; error: string } {
  try { const raw = localStorage.getItem(STORAGE_KEY); return { notes: raw ? parseNotebook(raw) : [], error: "" }; }
  catch { return { notes: [], error: "无法读取原笔记。原数据没有被覆盖，请先检查浏览器存储设置或使用导出备份。" }; }
}

function App() {
  const [route, setRoute] = useState<Route>(initialRoute);
  const [menu, setMenu] = useState(false);
  const [selected, setSelected] = useState(0);
  const [query, setQuery] = useState("");
  const [initial] = useState(loadNotes);
  const [notes, setNotes] = useState(initial.notes);
  const [notice, setNotice] = useState(initial.error);
  const [company, setCompany] = useState("");
  const [thesis, setThesis] = useState("");
  const [counter, setCounter] = useState("");
  const [reviewDate, setReviewDate] = useState("");
  const [editing, setEditing] = useState<string | null>(null);
  const sample = samples[selected];
  // Hash navigation works on project Pages without a server-side SPA fallback.
  useEffect(() => {
    const onHashChange = () => setRoute(initialRoute());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);
  function navigate(next: Route) { window.location.hash = next; setRoute(next); setMenu(false); setNotice(initial.error); }
  function saveNotes(next: Note[]): boolean {
    if (initial.error) { setNotice(initial.error); return false; }
    try { localStorage.setItem(STORAGE_KEY, serializeNotebook(next)); setNotes(next); return true; }
    catch { setNotice("浏览器没有保存成功，可能是存储空间不足或被禁用。请先导出已有笔记，当前输入仍保留。请勿关闭页面。"); return false; }
  }
  function addNote(event: FormEvent) {
    event.preventDefault();
    if (!company.trim() || !thesis.trim()) { setNotice("请填写公司和你的判断。"); return; }
    if (!editing && notes.length >= MAX_NOTES) { setNotice(`最多保存 ${MAX_NOTES} 条，请先导出整理。`); return; }
    const note: Note = { id: editing ?? crypto.randomUUID(), company: company.trim(), thesis: thesis.trim(), invalidation: counter.trim(), reviewDate, createdAt: notes.find(n => n.id === editing)?.createdAt ?? new Date().toISOString() };
    const next = editing ? notes.map(n => n.id === editing ? note : n) : [note, ...notes];
    if (saveNotes(next)) { resetForm(); setNotice("已保存到本浏览器。不会上传，也不会自动同步到完整服务。"); }
  }
  function resetForm() { setCompany(""); setThesis(""); setCounter(""); setReviewDate(""); setEditing(null); }
  function exportNotes() {
    const blob = new Blob([serializeNotebook(notes)], { type: "application/json" });
    const url = URL.createObjectURL(blob); const a = document.createElement("a");
    a.href = url; a.download = `xiami-notes-${new Date().toISOString().slice(0, 10)}.json`; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000); setNotice("已导出笔记 JSON，请妥善保存文件。");
  }
  async function importNotes(file?: File) {
    if (!file) return;
    try {
      if (file.size > 2_000_000) throw new Error("文件超过 2 MB，请先拆分。");
      const incoming = parseNotebook(await file.text()); const next = mergeNotes(notes, incoming);
      if (saveNotes(next)) setNotice(`导入完成，新增 ${next.length - notes.length} 条。相同编号保留已有内容。`);
    } catch (e) { setNotice(e instanceof Error ? e.message : "导入失败，原笔记未改变。"); }
  }
  return <div className="workspace">
    <aside className={`sidebar ${menu ? "open" : ""}`}>
      <a className="brand" href="#research" onClick={() => navigate("research")}><span className="brand-mark">虾</span><span>虾米看股<small>开源研究工作台</small></span></a>
      <button className="close-menu icon-button" aria-label="关闭导航" onClick={() => setMenu(false)}><X size={20}/></button>
      <nav aria-label="主导航">{routes.map(r => <a href={`#${r.id}`} key={r.id} aria-current={route === r.id ? "page" : undefined} onClick={() => navigate(r.id)}><r.icon size={19}/>{r.label}{r.id === "notebook" && <span className="count">{notes.length}</span>}</a>)}</nav>
      <div className="sidebar-bottom"><p>能独立运行的部分，<br/>先在这里用起来。</p><a href={REPO}><Github size={16}/> 完整源码 <ArrowUpRight size={14}/></a><a href="https://xiamimate.com/stocks/">完整在线服务 <ArrowUpRight size={14}/></a><small>作者个人维护，可能随时关闭。<br/>此 Pages 入口独立部署。</small></div>
    </aside>
    <div className="main-column">
      <header className="topbar"><button className="mobile-menu icon-button" aria-label="打开导航" onClick={() => setMenu(true)}><Menu size={21}/></button><span>虾米看股 <span className="slash">/</span> {routes.find(r => r.id === route)?.label}</span><a href={REPO}>GitHub <ArrowUpRight size={14}/></a></header>
      <div className="mode-banner"><span className="mode-dot"/><strong>静态体验</strong><span>样例为虚构数据 · 无实时行情、AI 调用或自动提醒</span><a href="#guide" onClick={() => navigate("guide")}>了解可用功能</a></div>
      <main id="main-content">
        {route === "research" && <>
          <div className="page-heading"><div><p className="eyebrow">把判断留下，把变化看清</p><h1>先看事实，再做决定。</h1><p>从一家公司开始，把理由、反证和下一步放在一起。</p></div><button onClick={() => { navigate("notebook"); resetForm(); }}>写下我的判断 <NotebookPen size={17}/></button></div>
          <div className="sample-notice">以下三家公司、财务和走势全部为虚构教学样例，不对应真实证券。</div>
          <div className="research-layout">
            <section className="company-list" aria-label="样例公司"><label className="search"><Search size={16}/><input aria-label="搜索样例公司" placeholder="搜索样例公司" value={query} onChange={e => setQuery(e.target.value)}/></label>{samples.map((s, i) => s.name.includes(query) || s.sector.includes(query) ? <button key={s.id} className={`company-item ${i === selected ? "selected" : ""}`} onClick={() => setSelected(i)}><span><strong>{s.name}</strong><small>{s.sector} · 虚构样例</small></span><ChevronRight size={18}/></button> : null)}{!samples.some(s => s.name.includes(query) || s.sector.includes(query)) && <p className="quiet">没有匹配样例。这里不查询实时股票。</p>}<div className="list-note">三个研究问题<br/><b>增长有没有现金？<br/>扩张有没有回报？<br/>便宜有没有理由？</b></div></section>
            <article className="research-sheet" key={sample.id}>
              <div className="sheet-heading"><div><span className="tag">{sample.sector} / 演示</span><h2>{sample.name}</h2></div><span className="pill">待核对</span></div>
              <div className="judgment"><span>当前研究重点</span><h3>{sample.title}</h3><p>{sample.thesis}</p></div>
              <dl className="metrics">{sample.metrics.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
              <div className="chart-heading"><h3>价格变化不等于理由变化</h3><span>18 个虚构观察点</span></div>
              <PriceChart values={sample.prices}/>
              <div className="evidence-columns"><section><h3>看到了什么</h3><ul>{sample.evidence.map(e => <li key={e}>{e}</li>)}</ul></section><section><h3>接下来查什么</h3><ul>{sample.next.map(e => <li key={e}>{e}</li>)}</ul></section></div>
              <div className="counter"><strong>什么会推翻这个判断？</strong><p>{sample.counter}</p></div>
              <div className="sheet-actions"><button onClick={() => navigate("valuation")}>用这组样例试算估值 <Calculator size={16}/></button><button className="secondary" onClick={() => { resetForm(); setCompany(`${sample.name}（虚构样例）`); setThesis(sample.thesis); setCounter(sample.counter); navigate("notebook"); }}>复制到我的笔记</button></div>
            </article>
          </div>
        </>}
        {route === "valuation" && <Valuation key={sample.id} sample={sample}/>}
        {route === "notebook" && <>
          <div className="page-heading"><div><p className="eyebrow">留下当时的依据</p><h1>我的研究笔记</h1><p>保存在本浏览器。清理网站数据会丢失，请定期导出；不要在公共电脑记录隐私。</p></div><div className="inline-actions"><button className="secondary" onClick={exportNotes}><Download size={16}/>导出</button><label className="button secondary upload"><Upload size={16}/>导入<input type="file" accept=".json,application/json" aria-label="导入笔记 JSON" onChange={e => { void importNotes(e.target.files?.[0]); e.target.value = ""; }}/></label></div></div>
          <div role="status" aria-live="polite" className={notice ? "notice" : ""}>{notice}</div>
          <div className="notebook-layout"><form className="note-form" onSubmit={addNote}><h2>{editing ? "修改判断" : "写一条判断"}</h2><label>公司或研究主题<input required maxLength={100} value={company} onChange={e => setCompany(e.target.value)} placeholder="例如：一家公司的回款变化"/></label><label>现在怎么看<textarea required maxLength={6000} rows={5} value={thesis} onChange={e => setThesis(e.target.value)} placeholder="写理由，不只写看涨或看跌。"/></label><label>什么会改变我的判断<textarea maxLength={6000} rows={3} value={counter} onChange={e => setCounter(e.target.value)} placeholder="例如：连续两期回款恶化。"/></label><label>下次复核日期<input type="date" value={reviewDate} onChange={e => setReviewDate(e.target.value)}/></label><small>日期只记录在笔记里，不会产生自动提醒。</small><div className="inline-actions"><button type="submit" disabled={Boolean(initial.error)}><Check size={16}/>保存到本浏览器</button>{editing && <button type="button" className="secondary" onClick={resetForm}>取消修改</button>}</div></form>
          <section className="notes-list" aria-label="已保存笔记"><h2>已记录 <span>{notes.length}</span></h2>{notes.length === 0 ? <div className="empty-note"><NotebookPen size={32}/><h3>不必写长篇报告。</h3><p>写清“为什么关注”和“什么情况会认错”，就能给下次判断留下参照。</p></div> : notes.map(note => <article className="saved-note" key={note.id}><div className="note-meta"><h3>{note.company}</h3><time>{new Date(note.createdAt).toLocaleDateString("zh-CN")}</time></div><p>{note.thesis}</p>{note.invalidation && <div className="note-counter"><b>反证条件</b><p>{note.invalidation}</p></div>}<footer><span>{note.reviewDate ? `复核日期：${note.reviewDate}` : "未设置复核日期"}</span><div><button className="text-button" onClick={() => { setEditing(note.id); setCompany(note.company); setThesis(note.thesis); setCounter(note.invalidation); setReviewDate(note.reviewDate); }}>修改</button><button className="text-button" onClick={() => { if (window.confirm(`删除「${note.company}」这条笔记？`)) { if (saveNotes(notes.filter(n => n.id !== note.id))) { if (editing === note.id) resetForm(); setNotice("笔记已删除。"); } } }}>删除</button></div></footer></article>)}</section></div>
        </>}
        {route === "guide" && <Guide/>}
      </main>
      <footer className="page-footer"><span>虾米看股 · 同一个完整开源仓库</span><a href={`${REPO}/blob/main/LICENSE`}>AGPL-3.0</a><a href={`${REPO}/issues`}>反馈问题</a></footer>
    </div>
  </div>;
}

function PriceChart({ values }: { values: readonly number[] }) {
  const min = Math.min(...values) - 2, max = Math.max(...values) + 2;
  const points = values.map((v, i) => `${40 + i / (values.length - 1) * 660},${160 - (v - min) / (max - min) * 135}`).join(" ");
  return <svg className="price-chart" viewBox="0 0 730 200" role="img" aria-label="虚构价格走势，不代表真实证券历史"><defs><linearGradient id="price-fill" x1="0" x2="0" y1="0" y2="1"><stop stopColor="#16857a" stopOpacity=".14"/><stop offset="1" stopColor="#16857a" stopOpacity="0"/></linearGradient></defs>{[min, (max + min) / 2, max].map(v => { const y = 160 - (v - min) / (max - min) * 135; return <g key={v}><line x1="40" x2="700" y1={y} y2={y} stroke="#e4ebed"/><text x="4" y={y + 4} fill="#6a7d86" fontSize="12">{v.toFixed(0)}</text></g>; })}<polygon points={`40,165 ${points} 700,165`} fill="url(#price-fill)"/><polyline points={points} fill="none" stroke="#16857a" strokeWidth="2.5" strokeLinejoin="round"/><text x="40" y="192" fill="#6a7d86" fontSize="12">样例起点</text><text x="640" y="192" fill="#6a7d86" fontSize="12">样例终点</text></svg>;
}

function Valuation({ sample }: { sample: typeof samples[number] }) {
  const [revenue, setRevenue] = useState<number>(sample.revenue), [shares, setShares] = useState<number>(sample.shares);
  const [years, setYears] = useState(3), [discount, setDiscount] = useState(10);
  const [scenarios, setScenarios] = useState([{ name: "保守", growth: 0, margin: sample.margin * .8, pe: sample.pe * .8 }, { name: "中性", growth: sample.growth, margin: sample.margin, pe: sample.pe }, { name: "乐观", growth: sample.growth + 10, margin: sample.margin * 1.2, pe: sample.pe * 1.2 }]);
  const factsValid = [revenue, shares, years, discount].every(Number.isFinite) && revenue > 0 && shares > 0 && years >= 1 && years <= 30 && discount >= 0 && discount <= 100;
  return <><div className="page-heading"><div><p className="eyebrow">把假设摊开，而不是猜一个目标价</p><h1>三种情景，三组结果。</h1><p>复用完整项目的估值公式。初始值来自 {sample.name} 的虚构样例，可改成自己的输入。</p></div></div><div className="valuation-facts">{[{ label: "起点年营收（亿元）", value: revenue, set: setRevenue, min: .01, max: undefined }, { label: "总股本（亿股）", value: shares, set: setShares, min: .01, max: undefined }, { label: "预测年数", value: years, set: setYears, min: 1, max: 30 }, { label: "折现率（%）", value: discount, set: setDiscount, min: 0, max: 100 }].map(f => <label key={f.label}>{f.label}<input type="number" value={Number.isNaN(f.value) ? "" : f.value} min={f.min} max={f.max} step="any" onChange={e => f.set(e.target.valueAsNumber)}/></label>)}</div>
    {!factsValid && <p className="notice" role="status">请输入有效数值：营收和股本大于 0，年数 1–30，折现率 0–100%。</p>}
    <div className="scenario-grid">{scenarios.map((s, i) => {
      const valid = factsValid && [s.growth, s.margin, s.pe].every(Number.isFinite) && s.growth > -100 && s.margin >= 0 && s.margin <= 100 && s.pe > 0;
      const value = valid ? valueOf({ revenueGrowth: s.growth, netMargin: s.margin, exitPe: s.pe }, { baseRevenue: revenue * 1e8, shares: shares * 1e8, years, discountRate: discount }) : null;
      const perShare = value?.perShare != null && Number.isFinite(value.perShare) ? value.perShare.toFixed(2) : "—";
      return <section className={`scenario scenario-${i}`} key={s.name}><h2>{s.name}</h2><p className="scenario-value"><span>折现后每股估值（元）</span><strong>{perShare}</strong></p>{([{ field: "growth", label: "收入年增（%）", min: -99, max: undefined }, { field: "margin", label: "净利率（%）", min: 0, max: 100 }, { field: "pe", label: "退出 PE（倍）", min: .01, max: undefined }] as const).map(f => <label key={f.field}>{f.label}<input type="number" step="any" min={f.min} max={f.max} value={Number.isNaN(s[f.field]) ? "" : s[f.field]} onChange={e => setScenarios(scenarios.map((v, j) => j === i ? { ...v, [f.field]: e.target.valueAsNumber } : v))}/></label>)}<div className="scenario-result"><p>期末营收 <b>{inYi(value?.futureRevenue)}</b></p><p>期末净利润 <b>{inYi(value?.futureProfit)}</b></p></div>{!valid && <small role="status">请检查输入范围，当前不计算估值。</small>}</section>;
    })}</div><section className="formula"><h2>怎么算的</h2><p>未来营收 = 当前营收 ×（1 + 收入年增）<sup>年数</sup><br/>未来利润 = 未来营收 × 净利率<br/>每股估值 = 未来利润 × 退出 PE ÷（1 + 折现率）<sup>年数</sup> ÷ 总股本</p><p>不含未来分红、增发和股本变化。假设由你提供，结果不代表预测，也不是买卖信号。负利润不适合用这套 PE 方法。输入仅用于当前页面，刷新后恢复样例。</p><a href={`${REPO}/blob/main/apps/web/src/lib/valuation.ts`}>查看完整项目的计算代码 <ArrowUpRight size={14}/></a></section></>;
}

function Guide() {
  return <><div className="page-heading"><div><p className="eyebrow">选一个适合自己的使用方式</p><h1>先体验，需要时再部署。</h1><p>Pages 是完整版项目的静态入口。完整前后端和助手源码都在同一个仓库。</p></div></div>
    <section className="guide-section"><h2>这个页面可以做什么</h2><div className="table-scroll"><table><thead><tr><th>功能</th><th>当前 Pages</th><th>自己运行完整服务</th></tr></thead><tbody>{[["研究样例与价格图", "虚构样例，可切换浏览", "公司档案与来源数据"], ["三情景估值", "可修改输入，即时计算", "计算并保存到研究库"], ["个人判断", "本浏览器保存、修改、导入导出", "数据库记录与版本历史"], ["行情、财报与公告", "不提供实时查询", "接入数据源后同步"], ["AI 研究与聊天", "不调用模型", "配置模型后使用"], ["飞书和自动提醒", "不运行、不发送", "配置机器人及后台服务"]].map(row => <tr key={row[0]}>{row.map(cell => <td key={cell}>{cell}</td>)}</tr>)}</tbody></table></div></section>
    <section className="guide-section"><h2>在自己的电脑运行</h2><p>需要 Git、Node.js 22+、Python 3.11+。先准备代码和依赖：</p><pre><code>{`git clone ${REPO}.git\ncd xiamimate-stock-lab\nnpm ci\npython3 -m venv .venv\nsource .venv/bin/activate\npip install -e '.[dev]'\ncp .env.example .env`}</code></pre><p>Windows 用户用 PowerShell 的 <code>.venv\Scripts\Activate.ps1</code> 激活环境。然后在两个终端分别启动：</p><pre><code>{`# 终端一：仅在本机开放 API\npython -m uvicorn stock_decision.main:app \\\n  --app-dir apps/api --host 127.0.0.1 --port 8108\n\n# 终端二：独立前端（根路径）\nnpm run dev:standalone`}</code></pre><p>打开 <code>http://127.0.0.1:5217/</code>。模型功能需要在本机 <code>.env</code> 填写自己的配置；不填也可先使用非 AI 功能。行情和财报同步依赖第三方数据源及网络。</p><p>本机数据库默认在 <code>var/stock_decision.db</code>。部署到公网前必须配置登录与数据隔离，不能把本机开放模式直接暴露到互联网。</p><a href={`${REPO}/blob/main/README.md`}>完整 README <ArrowUpRight size={14}/></a></section>
    <section className="guide-section"><h2>把助手带到飞书</h2><p>完整项目支持查股票、记判断、盯变化、核对计划。飞书需要后台服务、模型配置和自己的机器人应用。这里不会代你创建机器人，也不会读取作者的本地助手。</p><a href={`${REPO}/blob/main/apps/assistant/README.md`}>助手安装与接入说明 <ArrowUpRight size={14}/></a></section>
    <section className="guide-section"><h2>只想部署这个 Pages 页面</h2><p>Fork 仓库，在 Settings → Pages 选择 GitHub Actions，在 Actions 中运行 Publish GitHub Pages。之后 main 分支相关文件更新会自动部署。自定义仓库名也会自动生成正确路径。</p><pre><code>{`# 本地预览静态页面\nnpm ci\nnpm run build:pages\nnpm run preview:pages`}</code></pre><p>这是独立静态构建，不读取 .env、数据库或助手配置，也不请求作者服务器。笔记 JSON 用于本页面备份，不自动导入完整服务。</p></section>
    <section className="hosted-note"><h2>想使用作者的在线服务？</h2><p>作者个人维护，可能随时暂停或关闭，链接可能失效。不要把它当作唯一的数据备份。</p><a className="button secondary" href="https://xiamimate.com/stocks/">打开完整在线服务 <ArrowUpRight size={16}/></a><a href="https://xiamimate.com">虾米伙伴</a></section>
  </>;
}

createRoot(document.getElementById("root")!).render(<StrictMode><App/></StrictMode>);
