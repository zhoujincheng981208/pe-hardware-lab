# -*- coding: utf-8 -*-
"""生成器件损耗与结温评估 Excel 三区计算表（两种器件各一页）"""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import calc_core as c

wb = Workbook()
H1 = PatternFill('solid', fgColor='1E3A5F')
YEL = PatternFill('solid', fgColor='FFF3CF')
GRY = PatternFill('solid', fgColor='EEF3F8')
GRN = PatternFill('solid', fgColor='E3F6EA')
HD = PatternFill('solid', fgColor='D9E2EC')
WHITEB = Font(color='FFFFFF', bold=True, size=13)
BOLD = Font(bold=True)
thin = Side(style='thin', color='CBD5E1')
BD = Border(left=thin, right=thin, top=thin, bottom=thin)

def kv(ws, row, label, val, unit, fill, note=''):
    for col, v in enumerate([label, val, unit, note], 1):
        cell = ws.cell(row, col, v); cell.fill = fill; cell.border = BD

def section(ws, row, title, fill):
    ws.cell(row, 1, title).font = BOLD
    for col in range(1, 5):
        ws.cell(row, col).fill = fill; ws.cell(row, col).border = BD

INPUTS = [
 ('VDC','直流母线V',c.VDC,'V'),('IRMS','桥臂电流RMS',c.IRMS,'A'),('IAVG','桥臂电流均值',c.IAVG,'A'),
 ('FSW_KHZ','开关频率',c.FSW_KHZ,'kHz'),('TA','环境温度',c.TA,'°C'),
 ('N_PARALLEL','并联器件数',c.N_PARALLEL,''),('K_IMBAL','不均衡系数',c.K_IMBAL,''),
 ('RTH_JC','Rth结壳',c.RTH_JC,'K/W'),('RTH_CS','Rth壳散热器',c.RTH_CS,'K/W'),('RTH_SA','Rth散热器环境',c.RTH_SA,'K/W'),
 ('RDS_ON_25','Rds25',c.RDS_ON_25,'mΩ'),('RDS_TCO','Rds温系',c.RDS_TCO,'/K'),
 ('EON_REF','Eon参考',c.EON_REF,'mJ'),('EOFF_REF','Eoff参考',c.EOFF_REF,'mJ'),('ERR_REF','Err参考',c.ERR_REF,'mJ'),
 ('KV','电压指数',c.KV,''),('KI','电流指数',c.KI,''),('ALPHA_T','SiC温敏',c.ALPHA_T,'/K'),
 ('VREF','E参考电压',c.VREF,'V'),('IREF','E参考电流',c.IREF,'A'),('TREF','E参考温度',c.TREF,'°C'),
 ('VCE0','Vce0',c.VCE0,'V'),('RCE','Rce',c.RCE,'mΩ'),
 ('EON_REF_I','Eon(IGBT)',c.EON_REF_I,'mJ'),('EOFF_REF_I','Eoff(IGBT)',c.EOFF_REF_I,'mJ'),
 ('ERR_REF_I','Err(IGBT)',c.ERR_REF_I,'mJ'),('ALPHA_T_I','IGBT温敏',c.ALPHA_T_I,'/K'),
 ('TJ_MAX','结温上限',c.TJ_MAX,'°C'),('NF_REF','寿命参考',c.NF_REF,''),
 ('DT_LIFE_REF','寿命参考温差',c.DT_LIFE_REF,'K'),('M_COFFIN','Coffin指数',c.M_COFFIN,''),
 ('CYC_PER_YR','年循环次数',c.CYC_PER_YR,''),
]

for idx, dev in enumerate(['SiC', 'IGBT']):
    ws = wb.active if idx == 0 else wb.create_sheet()
    ws.title = f'{dev}结温评估'
    r = c.solve(dev)
    ws['A1'] = f'器件损耗与结温评估 · {dev}（黄=输入 / 灰=计算 / 绿=校核）'
    ws['A1'].font = WHITEB; ws['A1'].fill = H1; ws.merge_cells('A1:D1')
    row = 3; section(ws, row, '一、输入区（黄色可改）', HD); row += 1
    for key, name, val, unit in INPUTS:
        kv(ws, row, f'{key} {name}', val, unit, YEL); row += 1
    row += 1; section(ws, row, '二、计算区（灰色联动）', HD); row += 1
    calc_rows = [
        ('Irms/管','最热管电流',r['i_rms_dev'],'A'),('Rth总','总热阻',r['rth_total'],'K/W'),
        ('Pcond','导通损耗',r['p_cond'],'W'),('Eon','开通能量',r['eon'],'mJ'),
        ('Eoff','关断能量',r['eoff'],'mJ'),('Err','反恢复能量',r['err'],'mJ'),
        ('Psw','开关损耗',r['p_sw'],'W'),('Prr','反恢复损耗',r['p_rr'],'W'),
        ('Ptotal','总损耗',r['p_total'],'W'),('Tj','结温',r['Tj'],'°C'),
    ]
    if r['rds_mohm'] is not None:
        calc_rows.insert(2, ('Rds@Tj','热态导通电阻',r['rds_mohm'],'mΩ'))
    for name, label, val, unit in calc_rows:
        kv(ws, row, f'{name} {label}', val, unit, GRY); row += 1
    row += 1; section(ws, row, '三、校核区（绿色自动 PASS/FAIL）', HD); row += 1
    checks = [
        ('结温裕度>10K', r['margin'], f'{r["margin"]:.1f}K', r['ok_temp']),
        ('Tj<上限', r['Tj'], f'<{c.TJ_MAX}°C', r['Tj']<c.TJ_MAX),
        ('寿命>5年', r['life_yr'], f'{r["life_yr"]:.1f}年', r['life_yr']>5),
    ]
    for label, val, crit, ok in checks:
        ws.cell(row,1,label); ws.cell(row,2,crit); ws.cell(row,3,'PASS' if ok else 'FAIL')
        ws.cell(row,3).font = Font(bold=True, color='15803D' if ok else 'DC2626')
        for col in range(1,4): ws.cell(row,col).fill=GRN; ws.cell(row,col).border=BD
        row += 1
    ws.column_dimensions['A'].width = 26; ws.column_dimensions['B'].width = 16
    ws.column_dimensions['C'].width = 14; ws.column_dimensions['D'].width = 20

# 说明页
ws = wb.create_sheet('案例说明与方法')
notes = [
 '器件损耗与结温评估 · 案例说明与方法','',
 '一、解决的问题',
 '把器件选型从"查手册单点估算"升级为损耗-热-寿命的完整闭环，',
 '并支持 SiC / IGBT 同工况对比——高频下 IGBT 拖尾电流导致 Eoff 与温敏显著更大，',
 '同工况结温高、寿命短，这种差异单点估算看不出来。','',
 '二、Demonstration 工况',
 f'Vdc={c.VDC}V, Irms={c.IRMS}A, fsw={c.FSW_KHZ}kHz, Ta={c.TA}°C, 并联={c.N_PARALLEL}','',
 '三、核心结论（当前演示值）',
 f'SiC: 总损耗 {c.solve("SiC")["p_total"]:.1f}W, Tj={c.solve("SiC")["Tj"]:.1f}°C, 寿命 {c.solve("SiC")["life_yr"]:.1f}年',
 f'IGBT: 总损耗 {c.solve("IGBT")["p_total"]:.1f}W, Tj={c.solve("IGBT")["Tj"]:.1f}°C, 寿命 {c.solve("IGBT")["life_yr"]:.1f}年','',
 '四、公式',
 '导通: SiC=Rds(Tj)·Irms²; IGBT=Vce0·Iavg+Rce·Irms²',
 '开关: E=Eref·(Vdc/Vref)^kv·(I/Iref)^ki·(1+αT·(Tj−Tref))',
 '热: Tj=Ta+Ptotal·(RthJC+RthCS+RthSA), 迭代自洽',
 '寿命: Nf=Nf_ref·(ΔTj_ref/ΔTj)^m','',
 '五、假设与待核对',
 'Eon/Eoff/Err 均为 1200V/200A 级别工程典型值，必须由实际料号手册曲线重填。',
 'Rth 依赖散热设计需实测；寿命模型为工程估算，绝对数值仅供参考。',
 '网页/Excel/复算脚本三方结果交叉验证一致。',
]
for i, t in enumerate(notes, 1): ws.cell(i, 1, t)
ws.cell(1,1).font = Font(bold=True, size=14, color='1E3A5F')
ws.column_dimensions['A'].width = 92
wb.save('器件损耗结温计算表.xlsx')
print('已生成 器件损耗结温计算表.xlsx')
