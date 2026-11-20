# -*- coding: utf-8 -*-
"""
磁性元件综合设计平台 —— 计算内核
================================================
相比单电感计算器，本内核把"磁芯选型→绕组设计→损耗→温升→多方案优化"
串成完整设计闭环：
  1) 工况 → 电感量 L / 峰值电流 Ipk / 纹波 / 标幺值
  2) 磁芯几何 Ae/le/Ve/Aw（料号或 OD/ID/H 自定义）
  3) 安匝分配：Bdesign → N·n → 匝数 N / 叠堆芯数 n / 窗口利用率 Ku
  4) 绕组设计：股径/股数/层数 → 趋肤深度 δ → Dowell 公式 → 交流电阻系数 kac
  5) 损耗：铜损(含 kac 与温度系数) + 铁损(Steinmetz) → 总损耗
  6) 热：热阻 Rth → 稳态温升 ΔT（热态电阻迭代）
  7) 多方案：扫描 Bdesign，逐方案校核，按温升排序，推荐温升最小且全 PASS 方案

所有公式集中于此，网页 JS / 复算脚本共用同一套逻辑（verify_web.js 逐项比对）。
Dowell 公式出处：P. L. Dowell (1966)；圆线等效厚度 dw=√(π/4)·d（等面积变换）。
"""
import math

# ==================== 输入区（工程典型值，可改）====================
# 工况
P_KW      = 430.0     # 额定功率 kW
VLL       = 690.0     # 网侧线电压 V (RMS)
FGRID     = 50.0      # 电网频率 Hz
VDC       = 1100.0    # 直流母线 V
FSW_KHZ   = 5.0       # 开关频率 kHz
PF        = 0.99      # 功率因数
KRIPPLE   = 0.30      # 电流纹波率（相对额定相电流）
J         = 6.0       # 电流密度 A/mm²

# 磁芯（Kool Mu 60μ 环形，OD150；几何为工程参考值，需按实际料号核对）
OD        = 150.0     # 环形外径 mm
ID        = 90.0      # 环形内径 mm
H         = 30.0      # 单芯叠高 mm
MU_E      = 60.0      # 有效磁导率
STACK_K   = 0.95      # 叠片填充系数
BSAT      = 1.0       # 饱和磁密 T（Kool Mu 60μ 手册值）
STEIN_K   = 18.01     # Steinmetz k (mW/cm³, B:T, f:kHz) Magnetics 手册
STEIN_A   = 1.602     # B 指数
STEIN_B   = 1.401     # f 指数

# 绕组
STRAND_D  = 0.10      # 单股导体直径 mm（利兹线细股）
LAYERS    = 1         # 绕组层数 m（Dowell 中磁场从 0 升到最大的层数）
END_MARGIN= 20.0      # 平均每匝端部余量 mm

# 材料与热
RHO_CU    = 1.72e-8   # 铜电阻率 Ω·m @20°C
ALPHA_CU  = 0.00393   # 铜温度系数 /K
RTH       = 0.030     # 单电感→环境热阻 K/W（强制风冷参考，需实测）
MU0       = 4e-7 * math.pi

# 约束
S_SAT     = 0.80      # 饱和裕度上限 Bpk/Bsat
S_KU      = 0.50      # 窗口利用率上限
DT_LIMIT  = 50.0      # 稳态温升上限 K
LPU_MIN, LPU_MAX = 0.05, 0.20   # 标幺值合理区间

# 方案扫描
BD_START  = 0.30      # Bdesign 扫描起点 T
BD_END    = 0.78      # 终点 T（贴近饱和裕度 0.8·Bsat 边界）
BD_STEP   = 0.05      # 步长 T


def skin_depth(rho, f_hz):
    """趋肤深度 δ = √(2ρ/(ω·μ0)) [m]"""
    return math.sqrt(2 * rho / (2 * math.pi * f_hz * MU0))


def dowell_kac(strand_d_mm, f_hz, layers, rho=RHO_CU, temp_K=0.0):
    """
    Dowell 交流电阻系数 Fr = Rac/Rdc
      δ  = √(2ρ/(ωμ0))        趋肤深度
      dw = √(π/4)·d           圆线等效方厚（等面积变换）
      Δ  = dw/δ               穿透比
      ν2 = (sinhΔ−sinΔ)/(coshΔ+cosΔ)   邻近效应
      ν3 = (sinh2Δ+sin2Δ)/(cosh2Δ−cos2Δ) 趋肤效应
      Fr = Δ[ν3 + (2/3)(m²−1)ν2]
    小 Δ 用级数避免 0/0：Fr ≈ 1 + (2/9)(m²−1)Δ²
    temp_K: 相对 20°C 的温升，用于热态电阻率修正
    """
    rho_t = rho * (1 + ALPHA_CU * temp_K)
    delta = skin_depth(rho_t, f_hz)
    dw = math.sqrt(math.pi / 4) * strand_d_mm * 1e-3
    D = dw / delta
    m = max(1, layers)
    if D < 0.05:
        fr = 1 + (2.0 / 9.0) * (m * m - 1) * D * D
    else:
        nu2 = (math.sinh(D) - math.sin(D)) / (math.cosh(D) + math.cos(D))
        nu3 = (math.sinh(2*D) + math.sin(2*D)) / (math.cosh(2*D) - math.cos(2*D))
        fr = D * (nu3 + (2.0/3.0) * (m*m - 1) * nu2)
    return dict(kac=fr, delta_mm=delta*1e3, dw_mm=dw*1e3, D=D)


def geom():
    """单芯几何 Ae/le/Ve（SI），叠堆窗口用 ID×nH 矩形通道"""
    Ae = (OD - ID) / 2 * H * STACK_K * 1e-6       # m²
    le = math.pi * (OD + ID) / 2 * 1e-3           # m
    Ve = Ae * le * 1e6                            # cm³
    return dict(Ae=Ae, Ae_mm2=Ae*1e6, le=le, le_mm=le*1e3, Ve=Ve)


def electrical():
    """由工况求电感量、电流、标幺值"""
    iphase = P_KW*1000 / (math.sqrt(3)*VLL*PF)
    dip_pp = KRIPPLE * iphase
    L = VDC / (4 * FSW_KHZ*1000 * dip_pp)         # H（用户公式 Vdc/(4·fs·ΔIpp)）
    zbase = VLL**2 / (P_KW*1000)
    lbase = zbase / (2*math.pi*FGRID)
    lpu = L / lbase
    ipk = iphase*math.sqrt(2) + dip_pp/2
    irms = math.sqrt(iphase**2 + (dip_pp/math.sqrt(12))**2)  # 叠加纹波 RMS
    return dict(iphase=iphase, dip_pp=dip_pp, L=L, L_uH=L*1e6,
                lpu=lpu, lpu_pct=lpu*100, ipk=ipk, irms=irms,
                zbase=zbase, lbase=lbase)


def one_scheme(Bdesign, el, gm):
    """给定 Bdesign，求匝数/叠堆/绕组/损耗/温升/校核"""
    L, Ipk, Irms = el['L'], el['ipk'], el['irms']
    Ae, le, Ve = gm['Ae'], gm['le'], gm['Ve']

    # --- 安匝分配 ---
    AN = L * Ipk / (Bdesign * Ae)                 # N·n 安匝积
    Acu_wire = Irms / J                           # 每匝所需铜截面 mm²
    a_strand = math.pi/4 * STRAND_D**2            # 单股截面 mm²
    n_strand = math.ceil(Acu_wire / a_strand)     # 并联股数
    Awire = n_strand * a_strand                   # 实际导体截面 mm²

    # 叠堆窗口 = ID × (n·H)；约束 AN·Awire ≤ Ku·ID·H·n²
    n_min = math.sqrt(AN * Awire / (0.40 * ID * H))
    n = max(1, math.ceil(n_min))
    N = max(1, round(AN / n))
    bpk = L * Ipk / (N * n * Ae)                  # 实际峰值磁密
    Aw_stack = ID * (n * H)
    ku = N * Awire / Aw_stack

    # --- 绕组几何 ---
    stack_h = n * H
    mlt = (2*stack_h + (OD - ID) + END_MARGIN) * 1e-3   # 平均匝长 m

    # --- 铜损（热态电阻迭代 3 次）---
    dT = 25.0                                     # 温升初值
    for _ in range(3):
        rho_t = RHO_CU * (1 + ALPHA_CU*dT)
        rdc_temp = dowell_kac(STRAND_D, FSW_KHZ*1e3, LAYERS, RHO_CU, dT)
        kac = rdc_temp['kac']
        rdc = rho_t * N * mlt / (Awire*1e-6)       # 直流电阻 Ω（热态）
        rac = kac * rdc
        pcu = Irms**2 * rac

        # --- 铁损 Steinmetz ---
        dBac = L * el['dip_pp'] / (N*n*Ae)         # 交流磁密峰峰值 T
        bac = dBac / 2                             # 交流磁密幅值 T（Steinmetz 用幅值）
        pv = STEIN_K * bac**STEIN_A * FSW_KHZ**STEIN_B   # mW/cm³
        pfe = pv * (n*Ve) / 1000                   # W
        ptotal = pcu + pfe
        dT_new = ptotal * RTH
        if abs(dT_new - dT) < 0.01:
            dT = dT_new
            break
        dT = dT_new

    sat_margin = bpk / BSAT
    ok_sat = sat_margin < S_SAT
    ok_ku = ku < S_KU
    ok_dt = dT < DT_LIMIT
    all_ok = ok_sat and ok_ku and ok_dt

    return dict(
        Bdesign=Bdesign, AN=AN, n=n, N=N, n_strand=n_strand, Awire=Awire,
        bpk=bpk, sat_margin=sat_margin, ku=ku, Aw_stack=Aw_stack, stack_h=stack_h,
        mlt=mlt, kac=kac, delta_mm=rdc_temp['delta_mm'], dw_mm=rdc_temp['dw_mm'],
        Dpen=rdc_temp['D'], rdc=rdc, rac=rac, pcu=pcu, bac=bac, pv=pv,
        pfe=pfe, ptotal=ptotal, dT=dT,
        ok_sat=ok_sat, ok_ku=ok_ku, ok_dt=ok_dt, all_ok=all_ok,
    )


def solve():
    """主入口：工况 + 几何，扫描 Bdesign 生成方案表，推荐温升最优可行方案"""
    el = electrical()
    gm = geom()
    schemes = []
    bd = BD_START
    while bd <= BD_END + 1e-9:
        schemes.append(one_scheme(bd, el, gm))
        bd += BD_STEP
    feasible = [s for s in schemes if s['all_ok']]
    # 优化目标：温升最小（可行方案中）；无可行方案则取温升最小者
    pool = feasible if feasible else schemes
    best = min(pool, key=lambda s: s['dT'])
    return dict(el=el, gm=gm, schemes=schemes, best=best,
                has_feasible=bool(feasible))


if __name__ == '__main__':
    r = solve()
    el, gm = r['el'], r['gm']
    print("=" * 72)
    print("磁性元件综合设计平台 · 计算结果")
    print("=" * 72)
    print(f"电感 L={el['L_uH']:.1f}μH  标幺值={el['lpu_pct']:.1f}%  "
          f"Iphase={el['iphase']:.1f}A  Ipk={el['ipk']:.1f}A")
    print(f"单芯 Ae={gm['Ae_mm2']:.0f}mm²  le={gm['le_mm']:.0f}mm  Ve={gm['Ve']:.1f}cm³")
    d = dowell_kac(STRAND_D, FSW_KHZ*1e3, LAYERS)
    print(f"趋肤深度 δ@5kHz={d['delta_mm']:.3f}mm  dw={d['dw_mm']:.3f}mm  "
          f"穿透比Δ={d['D']:.3f}  kac(利兹)={d['kac']:.3f}")
    d4 = dowell_kac(1.0, FSW_KHZ*1e3, 4)
    print(f"对照：实心线 d=1mm,4层 → kac={d4['kac']:.3f}（利兹线优势明显）")
    print("-" * 72)
    print(f"{'Bdes':>5} {'n':>3} {'N':>4} {'Bpk':>6} {'Ku':>6} {'kac':>6} "
          f"{'Pcu':>7} {'Pfe':>6} {'Ptot':>7} {'ΔT':>6}  判定")
    for s in r['schemes']:
        flag = 'PASS' if s['all_ok'] else ('×sat' if not s['ok_sat'] else
               ('×Ku' if not s['ok_ku'] else '×温升'))
        print(f"{s['Bdesign']:5.2f} {s['n']:3d} {s['N']:4d} {s['bpk']:6.3f} "
              f"{s['ku']:6.3f} {s['kac']:6.3f} {s['pcu']:7.1f} {s['pfe']:6.1f} "
              f"{s['ptotal']:7.1f} {s['dT']:6.1f}  {flag}")
    b = r['best']
    print("-" * 72)
    print(f"推荐方案（温升最小且全 PASS）: Bdesign={b['Bdesign']:.2f}T  "
          f"n={b['n']}芯叠堆  N={b['N']}匝  ΔT={b['dT']:.1f}K")
    print(f"  饱和裕度={b['sat_margin']:.3f}  Ku={b['ku']:.3f}  "
          f"铜损={b['pcu']:.1f}W  铁损={b['pfe']:.1f}W")
