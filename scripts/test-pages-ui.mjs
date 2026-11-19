// React integration in an isolated DOM, not the user's browser or live accounts.
import { JSDOM } from 'jsdom';
import { build } from 'esbuild';
import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

const temp = await mkdtemp(join(tmpdir(), 'xiami-pages-ui-'));
const dom = new JSDOM('<html><body><div id="root"></div></body></html>', { url:'https://example.test/xiamimate-stock-lab/', pretendToBeVisual:true });
const win = dom.window;
for (const key of ['window','document','navigator','HTMLElement','HTMLInputElement','HTMLTextAreaElement','Element','Node','MutationObserver','CustomEvent','Event','MouseEvent','PopStateEvent','localStorage','getComputedStyle']) {
  Object.defineProperty(globalThis,key,{configurable:true,value:key==='window'?win:win[key]});
}
globalThis.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} };
win.ResizeObserver=globalThis.ResizeObserver;
win.matchMedia=() => ({matches:false,addEventListener(){},removeEventListener(){},addListener(){},removeListener(){}});
win.scrollTo=() => {};
win.HTMLElement.prototype.scrollIntoView=() => {};
win.HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','');};
const context = new Proxy({measureText:t=>({width:String(t).length*7}),createLinearGradient:()=>({addColorStop(){}}),createRadialGradient:()=>({addColorStop(){}})}, {get:(obj,key)=>key in obj?obj[key]:()=>{}});
win.HTMLCanvasElement.prototype.getContext=() => context;
let outbound=0;
globalThis.fetch=async () => {outbound++;throw new Error('Pages must not make API requests');};
const failures=[];
const realError=console.error;
console.error=(...args)=>{if(!String(args[0]).includes('width')&&!String(args[0]).includes('act('))failures.push(args.map(String).join(' '));};
const output=join(temp,'pages.mjs');
await build({entryPoints:['pages/src/main.tsx'],outfile:output,bundle:true,format:'esm',platform:'browser',jsx:'automatic',loader:{'.css':'empty'},define:{'import.meta.env.VITE_STATIC_PREVIEW':'"true"','import.meta.env.BASE_URL':'"/xiamimate-stock-lab/"','import.meta.env.DEV':'false','process.env.NODE_ENV':'"production"'},logLevel:'silent'});
await import(pathToFileURL(output).href);
async function until(check,label){const stop=Date.now()+6000;while(!check()){if(Date.now()>stop)throw new Error(`Timed out: ${label}\n${document.body.textContent.slice(-1600)}`);await new Promise(r=>setTimeout(r,20));}}
async function route(path){win.history.pushState({},'',`/xiamimate-stock-lab/#${path}`);win.dispatchEvent(new win.PopStateEvent('popstate'));await new Promise(r=>setTimeout(r,180));}
function click(selector,text){const el=[...document.querySelectorAll(selector)].find(e=>e.textContent.trim().includes(text));assert.ok(el,`Missing control: ${text}`);el.click();}
try {
  await until(()=>document.querySelector('.market-cockpit') || document.body.textContent.includes('海屿储能'),'dashboard');
  assert.equal(document.querySelectorAll('.sidebar .nav-section').length,5);
  assert.ok(document.querySelector('.pages-banner'));
  click('.sidebar button','公司');
  await until(()=>document.body.textContent.includes('云帆光联'),'company list');
  assert.ok(win.location.hash.includes('/companies'));
  await route('/companies/1');
  await until(()=>document.body.textContent.includes('海屿储能'),'company detail');
  click('button','财务与行业');
  await until(()=>document.body.textContent.includes('经营与财务趋势'),'financial chart panel');
  click('button','行情与估值');
  await until(()=>document.body.textContent.includes('每股价值'),'original valuation component');
  await route('/decision-loop');
  await until(()=>document.body.textContent.includes('海屿储能'),'tracking');
  await route('/portfolio');
  await until(()=>document.body.textContent.includes('虚构演示组合'),'portfolio');
  await route('/industry-chains');
  await until(()=>document.body.textContent.includes('产业链'),'chain');
  await route('/methods');
  await until(()=>document.body.textContent.includes('两分钟独白'),'methods');
  await route('/industries');
  await route('/screener');
  await route('/preferences');
  click('.pages-banner button','我的笔记');
  await until(()=>document.querySelector('dialog[open]'),'notebook');
  const form=document.querySelector('.pages-notebook form');
  const input=form.querySelector('input'); const area=form.querySelector('textarea');
  Object.getOwnPropertyDescriptor(win.HTMLInputElement.prototype,'value').set.call(input,'DOM 验收');
  input.dispatchEvent(new win.Event('input',{bubbles:true}));
  Object.getOwnPropertyDescriptor(win.HTMLTextAreaElement.prototype,'value').set.call(area,'保存一条明确的判断');
  area.dispatchEvent(new win.Event('input',{bubbles:true}));
  await new Promise(r=>setTimeout(r,30));
  form.dispatchEvent(new win.Event('submit',{bubbles:true,cancelable:true}));
  await until(()=>document.body.textContent.includes('已保存到本浏览器'),'save note');
  assert.ok(localStorage.getItem('xiamimate-stock-lab:pages:notebook:v1').includes('DOM 验收'));
  click('dialog button','关闭笔记');
  await until(()=>!document.querySelector('dialog'),'close note');
  click('.topbar button','写下一个判断');
  await until(()=>document.querySelector('dialog[open]'),'shared write entry');
  assert.equal(outbound,0,'Static mode must not call a backend');
  assert.deepEqual(failures,[],'No React errors');
  console.log('PASS: original navigation, company detail, tracking, portfolio, chains, methods, local note save and no API requests');
} finally {console.error=realError;dom.window.close();await rm(temp,{recursive:true,force:true});}
