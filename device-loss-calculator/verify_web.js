// 验证网页 core 与 Python 内核逐项一致（SiC + IGBT）
const fs = require('fs'), cp = require('child_process'), vm = require('vm');
const py = JSON.parse(cp.execSync('python export_core.py', {cwd: __dirname}).toString().trim());
const html = fs.readFileSync('index.html', 'utf8');
const m = html.match(/<script id="core">([\s\S]*?)<\/script>/);
if (!m) { console.error('未找到 core 脚本'); process.exit(1); }
const ctx = {}; vm.createContext(ctx); vm.runInContext(m[1], ctx);

let pass = 0, fail = 0;
function cmp(label, a, b, rel) {
  const ok = (a === null || b === null || typeof a === 'boolean') ? (a === b) :
    (Math.abs(a-b) <= (rel||1e-6)*Math.max(1, Math.abs(b)));
  if (ok) pass++; else { fail++; console.log(`  ✗ ${label}: web=${a} py=${b}`); }
}
['SiC','IGBT'].forEach(dev => {
  const w = ctx.solveDevice(py.params, dev), p = py[dev];
  ['n_parallel','i_rms_dev','i_avg_dev','rth_total','rds_mohm','p_cond','eon','eoff','err',
   'p_sw','p_rr','p_total','Tj','margin','ok_temp','dTj','nf','life_yr'].forEach(k => {
    cmp(`${dev}.${k}`, w[k], p[k], 1e-7);
  });
});
console.log(`\n===== 合计 ${pass} 通过 / ${fail} 失败 =====`);
process.exit(fail ? 1 : 0);
