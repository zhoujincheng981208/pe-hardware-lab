# -*- coding: utf-8 -*-
"""导出内核结果供 verify_web.js 比对（不打印 token，纯数值）"""
import json, calc_core as c

r = c.solve()
out = {
    'el': {k: r['el'][k] for k in ['iphase','dip_pp','L','L_uH','lpu','lpu_pct','ipk','irms']},
    'gm': {k: r['gm'][k] for k in ['Ae','Ae_mm2','le','le_mm','Ve']},
    'schemes': [],
    'best_idx': None,
}
# 方案按 dT 排序前的原始清单，best 用 Bdesign 标识
for i, s in enumerate(r['schemes']):
    out['schemes'].append({
        'Bdesign': s['Bdesign'], 'n': s['n'], 'N': s['N'],
        'n_strand': s['n_strand'], 'Awire': s['Awire'],
        'bpk': s['bpk'], 'sat_margin': s['sat_margin'], 'ku': s['ku'],
        'kac': s['kac'], 'delta_mm': s['delta_mm'], 'pcu': s['pcu'],
        'bac': s['bac'], 'pv': s['pv'], 'pfe': s['pfe'], 'ptotal': s['ptotal'],
        'dT': s['dT'], 'all_ok': s['all_ok'],
    })
out['best_Bdesign'] = r['best']['Bdesign']
out['has_feasible'] = r['has_feasible']
out['params'] = {k: getattr(c, k) for k in ['P_KW','VLL','FGRID','VDC','FSW_KHZ','PF',
    'KRIPPLE','J','OD','ID','H','STACK_K','BSAT','STEIN_K','STEIN_A','STEIN_B',
    'STRAND_D','LAYERS','END_MARGIN','RHO_CU','RTH','S_SAT','S_KU','DT_LIMIT',
    'BD_START','BD_END','BD_STEP']}
print(json.dumps(out, ensure_ascii=False))
