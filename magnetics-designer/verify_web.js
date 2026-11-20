// 验证网页 core 脚本与 Python 内核逐项一致
const fs = require('fs');
const cp = require('child_process');
const vm = require('vm');

// 1) 取 Python 内核结果
const pyOut = cp.execSync('python export_core.py', {cwd: __dirname}).toString().trim();
const py = JSON.parse(pyOut);

// 2) 抽取网页 <script id="core"> 并在沙箱执行
const html = fs.readFileSync('index.html', 'utf8');
const m = html.match(/<script id="core">([\s\S]*?)<\/script>/);
if (!m) { console.error('未找到 core 脚本'); process.exit(1); }
const ctx = {};
vm.createContext(ctx);
vm.runInContext(m[1], ctx);
const web = ctx.solve(py.params);

let pass = 0, fail = 0;
const tol = 1e-6;
function cmp(label, a, b, rel) {
  const ok = (typeof a === 'boolean') ? (a === b) :
    (Math.abs(a - b) <= (rel ? rel * Math.max(1, Math.abs(b)) : tol));
  if (ok) { pass++; } else { fail++; console.log(`  ✗ ${label}: web=${a} py=${b}`); }
}

// 3) 电气 + 几何
['iphase','dip_pp','L','L_uH','lpu','lpu_pct','ipk','irms'].forEach(k => cmp('el.'+k, web.el[k], py.el[k], 1e-9));
['Ae','Ae_mm2','le','le_mm','Ve'].forEach(k => cmp('gm.'+k, web.gm[k], py.gm[k], 1e-9));

// 4) 方案（按 Bdesign 对齐，逐项比对）
const pyMap = {};
py.schemes.forEach(s => pyMap[s.Bdesign.toFixed(4)] = s);
console.log(`方案数: web=${web.schemes.length} py=${py.schemes.length}`);
cmp('方案数量', web.schemes.length, py.schemes.length);
web.schemes.forEach(ws => {
  const ps = pyMap[ws.Bdesign.toFixed(4)];
  if (!ps) { fail++; console.log(`  ✗ 缺方案 Bdesign=${ws.Bdesign}`); return; }
  ['n','N','n_strand','all_ok'].forEach(k => cmp(`B${ws.Bdesign.toFixed(2)}.${k}`, ws[k], ps[k]));
  ['Awire','bpk','sat_margin','ku','kac','delta_mm','pcu','bac','pv','pfe','ptotal','dT']
    .forEach(k => cmp(`B${ws.Bdesign.toFixed(2)}.${k}`, ws[k], ps[k], 1e-8));
});
// 5) 推荐方案
cmp('best.Bdesign', web.best.Bdesign, py.best_Bdesign);
cmp('has_feasible', web.has_feasible, py.has_feasible);

console.log(`\n===== 合计 ${pass} 通过 / ${fail} 失败 =====`);
process.exit(fail ? 1 : 0);
