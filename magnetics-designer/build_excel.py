# -*- coding: utf-8 -*-
"""生成磁性元件综合设计的 Excel 三区计算表（输入黄/计算灰/校核绿）"""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import calc_core as c

wb = Workbook()
ws = wb.active
ws.title = '磁性元件设计'

H1 = PatternFill('solid', fgColor='1E3A5F')
YEL = PatternFill('solid', fgColor='FFF3CF')
GRY = PatternFill('solid', fgColor='EEF3F8')
GRN = PatternFill('solid', fgColor='E3F6EA')
HD = PatternFill('solid', fgColor='D9E2EC')
WHITEB = Font(color='FFFFFF', bold=True, size=13)
BOLD = Font(bold=True)
thin = Side(style='thin', color='CBD5E1')
BD = Border(left=thin, right=thin, top=thin, bottom=thin)

r = c.solve()
el, gm, best = r['el'], r['gm'], r['best']

ws['A1'] = '磁性元件综合设计平台 · 计算表（黄=输入 / 灰=计算 / 绿=校核）'
ws['A1'].font = WHITEB; ws['A1'].fill = H1
ws.merge_cells('A1:F1')

def section(row, title, fill):
    ws.cell(row, 1, title).font = BOLD
    for col in range(1, 7):
        ws.cell(row, col).fill = fill; ws.cell(row, col).border = BD

def kv(row, label, val, unit, fill, note=''):
    ws.cell(row, 1, label); ws.cell(row, 2, val); ws.cell(row, 3, unit); ws.cell(row, 4, note)
    for col in range(1, 5):
        ws.cell(row, col).fill = fill; ws.cell(row, col).border = BD

# 输入区
row = 3
section(row, '一、输入区（黄色可改）', HD); row += 1
inputs = [
    ('P_KW','额定功率',c.P_KW,'kW'),('VLL','网侧线电压',c.VLL,'V'),('VDC','直流母线',c.VDC,'V'),
    ('FSW_KHZ','开关频率',c.FSW_KHZ,'kHz'),('FGRID','电网频率',c.FGRID,'Hz'),('PF','功率因数',c.PF,''),
    ('KRIPPLE','电流纹波率',c.KRIPPLE,''),('J','电流密度',c.J,'A/mm²'),
    ('OD','外径 OD',c.OD,'mm'),('ID','内径 ID',c.ID,'mm'),('H','单芯叠高',c.H,'mm'),
    ('STACK_K','叠片系数',c.STACK_K,''),('BSAT','饱和磁密',c.BSAT,'T'),
    ('STEIN_K','Steinmetz k',c.STEIN_K,'mW/cm³'),('STEIN_A','B指数',c.STEIN_A,''),('STEIN_B','f指数',c.STEIN_B,''),
    ('STRAND_D','单股直径',c.STRAND_D,'mm'),('LAYERS','绕组层数',c.LAYERS,''),
    ('END_MARGIN','端部余量',c.END_MARGIN,'mm'),('RHO_CU','铜电阻率',c.RHO_CU,'Ω·m'),
    ('RTH','热阻 Rth',c.RTH,'K/W'),('S_SAT','饱和上限',c.S_SAT,''),('S_KU','窗口上限',c.S_KU,''),
    ('DT_LIMIT','温升上限',c.DT_LIMIT,'K'),('BD_START','Bdesign起',c.BD_START,'T'),
    ('BD_END','Bdesign止',c.BD_END,'T'),('BD_STEP','扫描步长',c.BD_STEP,'T'),
]
for key, name, val, unit in inputs:
    kv(row, f'{key}  {name}', val, unit, YEL); row += 1

# 计算区
row += 1
section(row, '二、计算区（灰色联动）', HD); row += 1
calc_rows = [
    ('L','电感量', best and el['L_uH'], 'μH'),('lpu','标幺值', el['lpu_pct'],'%'),
    ('Iphase','额定相电流', el['iphase'],'A'),('Ipk','峰值电流', el['ipk'],'A'),
    ('Ae','单芯截面', gm['Ae_mm2'],'mm²'),('le','磁路长', gm['le_mm'],'mm'),('Ve','单芯体积', gm['Ve'],'cm³'),
    ('δ','趋肤深度', c.dowell_kac(c.STRAND_D,c.FSW_KHZ*1e3,c.LAYERS)['delta_mm'],'mm'),
    ('kac(推荐)','交流电阻系数', best['kac'],''),
    ('推荐n','叠堆芯数', best['n'],'个'),('推荐N','匝数', best['N'],'匝'),
    ('股数','并联股数', best['n_strand'],'股'),
    ('Bpk','峰值磁密', best['bpk'],'T'),('Ku','窗口利用率', best['ku'],''),
    ('铜损','Pcu', best['pcu'],'W'),('铁损','Pfe', best['pfe'],'W'),
    ('总损耗','Ptotal', best['ptotal'],'W'),('温升','ΔT', best['dT'],'K'),
]
for name, label, val, unit in calc_rows:
    kv(row, f'{name}  {label}', val, unit, GRY); row += 1

# 校核区
row += 1
section(row, '三、校核区（绿色自动 PASS/FAIL）', HD); row += 1
checks = [
    ('饱和裕度 Bpk/Bsat', best['sat_margin'], f'<{c.S_SAT}', best['ok_sat']),
    ('窗口利用率 Ku', best['ku'], f'<{c.S_KU}', best['ok_ku']),
    ('稳态温升 ΔT', best['dT'], f'<{c.DT_LIMIT}K', best['ok_dt']),
    ('标幺值区间', el['lpu_pct'], '5%~20%', 0.05<=el['lpu']<=0.20),
]
for label, val, crit, ok in checks:
    ws.cell(row,1,label); ws.cell(row,2,val); ws.cell(row,3,crit); ws.cell(row,4,'PASS' if ok else 'FAIL')
    ws.cell(row,4).font = Font(bold=True, color='15803D' if ok else 'DC2626')
    for col in range(1,5): ws.cell(row,col).fill=GRN; ws.cell(row,col).border=BD
    row += 1

# 方案表
row += 1
section(row, '四、Bdesign 扫描方案表', HD); row += 1
hdr = ['Bdesign(T)','n','N','Bpk(T)','Ku','kac','铜损W','铁损W','总损耗W','ΔT(K)','判定']
for j, h in enumerate(hdr):
    cell = ws.cell(row, j+1, h); cell.fill = HD; cell.font = BOLD; cell.border = BD
row += 1
for s in sorted(r['schemes'], key=lambda x: x['dT']):
    vals = [s['Bdesign'],s['n'],s['N'],s['bpk'],s['ku'],s['kac'],s['pcu'],s['pfe'],s['ptotal'],s['dT'],'PASS' if s['all_ok'] else 'FAIL']
    for j, v in enumerate(vals):
        cell = ws.cell(row, j+1, v); cell.border = BD
        if s is best: cell.fill = GRN
    row += 1

# 说明页
ws2 = wb.create_sheet('案例说明与方法')
notes = [
 '磁性元件综合设计平台 · 案例说明与方法',
 '',
 '一、解决的问题',
 '把 LCL 电感单点计算升级为完整设计闭环：工况→磁芯→绕组→损耗→温升→多方案优选。',
 '大电流工况下铜损主导、铁损可忽略，温升最优常落在饱和边界附近，',
 '降匝数降铜损与饱和裕度相互制约——这种设计权衡单点计算看不出来。',
 '',
 '二、Demonstration 工况',
 f'P={c.P_KW}kW, Vll={c.VLL}V, Vdc={c.VDC}V, fs={c.FSW_KHZ}kHz, 纹波率={c.KRIPPLE}, J={c.J}A/mm²',
 f'磁芯 Kool Mu 60μ OD{c.OD}/ID{c.ID}/H{c.H}, Bsat={c.BSAT}T',
 '',
 '三、推荐方案',
 f'Bdesign={best["Bdesign"]:.2f}T, {best["n"]}芯叠堆, N={best["N"]}匝, {best["n_strand"]}股并绕',
 f'Bpk={best["bpk"]:.3f}T, Ku={best["ku"]:.3f}, ΔT={best["dT"]:.1f}K',
 '',
 '四、公式',
 'L=Vdc/(4·fs·ΔIpp); N·n=L·Ipk/(Bdesign·Ae)',
 'Dowell: Fr=Δ[ν3+(2/3)(m²−1)ν2], dw=√(π/4)·d, Δ=dw/δ, δ=√(2ρ/(ωμ0))',
 '铜损=Irms²·kac·Rdc(热态迭代); 铁损=k·Bac^α·f^β·n·Ve; 温升=(Pcu+Pfe)·Rth',
 '',
 '五、假设与待核对',
 'OD/ID/H、Rth、Steinmetz 系数均为工程参考值/手册值，需按实际料号与散热条件核对。',
 '网页/Excel/复算脚本三方结果交叉验证一致。',
]
for i, t in enumerate(notes, 1):
    ws2.cell(i, 1, t)
ws2.cell(1,1).font = Font(bold=True, size=14, color='1E3A5F')
ws2.column_dimensions['A'].width = 90
ws.column_dimensions['A'].width = 26
ws.column_dimensions['D'].width = 24

wb.save('磁性元件设计计算表.xlsx')
print('已生成 磁性元件设计计算表.xlsx')
