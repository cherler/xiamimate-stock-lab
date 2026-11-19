import { StrictMode, useEffect, useRef, useState, type FormEvent } from "react";
import { createRoot } from "react-dom/client";
import App from "../../apps/web/src/App";
import { ErrorBoundary } from "../../apps/web/src/ErrorBoundary";
import { MAX_NOTES, STORAGE_KEY, parseNotebook, serializeNotebook, mergeNotes, type Note } from "./notebook";
import "../../apps/web/src/styles.css";
import "./style.css";

const REPO = 'https://github.com/cherler/xiamimate-stock-lab';

function Notebook({ symbol, close }: { symbol: string; close: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [initial] = useState(() => {
    try { const raw = localStorage.getItem(STORAGE_KEY); return { notes: raw ? parseNotebook(raw) : [], error: '' }; }
    catch { return { notes: [] as Note[], error: '无法读取原笔记。原数据没有被覆盖，请检查浏览器存储或使用导出备份。' }; }
  });
  const [notes, setNotes] = useState(initial.notes), [notice, setNotice] = useState(initial.error);
  const [company, setCompany] = useState(symbol), [thesis, setThesis] = useState(''), [counter, setCounter] = useState(''), [reviewDate, setReviewDate] = useState('');
  const [editing, setEditing] = useState<string | null>(null);
  useEffect(() => { dialog.current?.showModal(); }, []);
  function save(next: Note[]) {
    if (initial.error) return false;
    try { localStorage.setItem(STORAGE_KEY, serializeNotebook(next)); setNotes(next); return true; }
    catch { setNotice('保存失败：浏览器存储不可用。输入仍保留，请勿关闭页面；已有笔记可先导出。'); return false; }
  }
  function clear() { setCompany(''); setThesis(''); setCounter(''); setReviewDate(''); setEditing(null); }
  function submit(event: FormEvent) {
    event.preventDefault();
    if (!company.trim() || !thesis.trim()) { setNotice('请填写公司和判断。'); return; }
    if (!editing && notes.length >= MAX_NOTES) { setNotice(`最多保存 ${MAX_NOTES} 条，请先导出整理。`); return; }
    const note: Note = { id: editing ?? crypto.randomUUID(), company:company.trim(), thesis:thesis.trim(), invalidation:counter.trim(), reviewDate, createdAt:notes.find(n => n.id === editing)?.createdAt ?? new Date().toISOString() };
    if (save(editing ? notes.map(n => n.id === editing ? note : n) : [note,...notes])) { clear(); setNotice('已保存到本浏览器。不会上传或自动同步到完整服务。'); }
  }
  function exportNotes() {
    const url = URL.createObjectURL(new Blob([serializeNotebook(notes)], {type:'application/json'}));
    const a = document.createElement('a'); a.href=url; a.download=`xiami-notes-${new Date().toISOString().slice(0,10)}.json`; a.click(); setTimeout(() => URL.revokeObjectURL(url),1000);
  }
  async function importNotes(file?: File) {
    if (!file) return;
    try {
      if (file.size > 2_000_000) throw new Error('文件超过 2 MB。');
      const next=mergeNotes(notes,parseNotebook(await file.text()));
      if (save(next)) setNotice(`导入完成，新增 ${next.length-notes.length} 条，相同编号保留已有内容。`);
    } catch(e) { setNotice(e instanceof Error ? e.message : '导入失败，原数据未改变。'); }
  }
  return <dialog ref={dialog} className="pages-dialog" onCancel={close}>
    <header><div><h2>我的笔记</h2><p>保存在本浏览器，不上传。复核日期只作记录，不发送提醒。</p></div><button className="secondary-action" onClick={close}>关闭笔记</button></header>
    <div className="pages-note-actions"><button className="secondary-action" onClick={exportNotes}>导出笔记</button><label className="secondary-action pages-upload">导入笔记<input aria-label="导入笔记 JSON" type="file" accept=".json" onChange={e => {void importNotes(e.target.files?.[0]);e.target.value='';}}/></label><span>清理网站数据会丢失笔记，请定期导出。</span></div>
    {notice && <p className="pages-note-status" role="status">{notice}</p>}
    <div className="pages-notebook"><form onSubmit={submit}><h3>{editing ? '修改判断' : '写下一个判断'}</h3>
      <label>公司或研究主题<input required maxLength={100} value={company} onChange={e => setCompany(e.target.value)}/></label>
      <label>现在怎么看<textarea required rows={4} maxLength={6000} value={thesis} onChange={e => setThesis(e.target.value)}/></label>
      <label>什么会改变判断<textarea rows={3} maxLength={6000} value={counter} onChange={e => setCounter(e.target.value)}/></label>
      <label>下次复核日期<input type="date" value={reviewDate} onChange={e => setReviewDate(e.target.value)}/></label>
      <button className="page-action" disabled={Boolean(initial.error)} type="submit">保存到本浏览器</button>{editing && <button className="secondary-action" type="button" onClick={clear}>取消修改</button>}
    </form><section aria-label="已保存笔记"><h3>已记录 {notes.length} 条</h3>{notes.length === 0 && <p>写清关注理由和反证条件，给下次判断留个参照。</p>}{notes.map(n => <article key={n.id}><h4>{n.company}</h4><p>{n.thesis}</p>{n.invalidation && <p><strong>反证条件：</strong>{n.invalidation}</p>}<small>{n.reviewDate ? `复核日期：${n.reviewDate}` : '未设置复核日期'}</small><div><button className="text-button" onClick={() => {setEditing(n.id);setCompany(n.company);setThesis(n.thesis);setCounter(n.invalidation);setReviewDate(n.reviewDate);}}>修改</button><button className="text-button" onClick={() => {if(window.confirm('删除这条笔记？') && save(notes.filter(v => v.id !== n.id))) {if(editing === n.id) clear();setNotice('已删除。');}}}>删除</button></div></article>)}</section></div>
  </dialog>;
}

function Guide({ close }: { close: () => void }) {
  const ref=useRef<HTMLDialogElement>(null);
  useEffect(() => {ref.current?.showModal();},[]);
  return <dialog className="pages-dialog pages-guide" ref={ref} onCancel={close}><header><h2>同一个虾米看股，两种运行方式</h2><button className="secondary-action" onClick={close}>关闭说明</button></header><h3>Pages：原站界面，虚构样例</h3><p>复用原站页面、导航、图表与估值组件。可以浏览公司档案、财务、产业链、持仓账本和应对报告，修改估值假设试算，并把个人想法保存在浏览器笔记。页面中的公司、行情、持仓、研究结论全部是虚构演示，不能当作真实投资分析。</p><h3>完整服务：接入自己的数据与助手</h3><p>行情同步、AI 研究、文件解析、飞书、自动提醒和数据库保存需要后台。Pages 不请求作者的接口，也不会把示例按钮的点击假装成已执行。</p><p><a href="https://xiamimate.com/stocks/">打开完整在线服务</a>（个人维护，可能随时关闭、链接失效）</p><h3>下载完整源码，在本机运行</h3><p>前端、API、CLI、MCP 与飞书助手都在同一仓库。</p><p><a href={REPO}>完整源码</a> · <a href={`${REPO}/blob/main/README.md`}>安装说明</a> · <a href={`${REPO}/blob/main/apps/assistant/README.md`}>飞书接入</a> · <a href={`${REPO}/blob/main/docs/PAGES.md`}>Pages 部署</a></p></dialog>;
}

function PagesApp() {
  const [notes, setNotes] = useState<{symbol:string} | null>(null), [guide, setGuide] = useState(false);
  const banner = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const listener=(event:Event) => setNotes({symbol:(event as CustomEvent<{symbol?:string}>).detail?.symbol ?? ''});
    window.addEventListener('xiami-preview-note',listener);
    const resize = () => document.documentElement.style.setProperty('--pages-banner-height',`${banner.current?.offsetHeight ?? 54}px`);
    const observer = new ResizeObserver(resize); if(banner.current)observer.observe(banner.current); resize();
    return () => {window.removeEventListener('xiami-preview-note',listener);observer.disconnect();};
  },[]);
  return <><div ref={banner} className="pages-banner"><div><strong>虾米看股 · Pages</strong><span>原站界面 / 虚构样例 / 非实时行情</span></div><nav aria-label="Pages 工具"><button onClick={() => setNotes({symbol:''})}>我的笔记</button><button onClick={() => setGuide(true)}>使用说明</button><a href={REPO}>源码</a><a href="https://xiamimate.com/stocks/">完整在线服务 ↗</a></nav></div><App/>{notes && <Notebook symbol={notes.symbol} close={() => setNotes(null)}/>} {guide && <Guide close={() => setGuide(false)}/>}</>;
}

createRoot(document.getElementById('root')!).render(<StrictMode><ErrorBoundary><PagesApp/></ErrorBoundary></StrictMode>);
