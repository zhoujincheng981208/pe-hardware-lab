# -*- coding: utf-8 -*-
"""导出内核两种器件结果供 verify_web.js 比对"""
import json, calc_core as c

out = {'params': {k: getattr(c, k) for k in [
    'DEVICE','VDC','IRMS','IAVG','FSW_KHZ','DUTY','TA','RTH_JC','RTH_CS','RTH_SA',
    'N_PARALLEL','K_IMBAL','RDS_ON_25','RDS_TCO','EON_REF','EOFF_REF','ERR_REF',
    'KV','KI','ALPHA_T','TREF','VREF','IREF','VCE0','RCE','EON_REF_I','EOFF_REF_I',
    'ERR_REF_I','ALPHA_T_I','TJ_MAX','DT_LIFE_REF','NF_REF','M_COFFIN','CYC_PER_YR']}}
for dev in ['SiC', 'IGBT']:
    r = c.solve(dev)
    out[dev] = {k: r[k] for k in ['device','Vdc','fsw_khz','n_parallel','i_rms_dev',
        'i_avg_dev','rth_total','rds_mohm','p_cond','eon','eoff','err','p_sw',
        'p_rr','p_total','Tj','margin','ok_temp','dTj','nf','life_yr']}
print(json.dumps(out, ensure_ascii=False))
