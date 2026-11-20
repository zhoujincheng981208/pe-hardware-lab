# -*- coding: utf-8 -*-
"""
器件损耗与结温评估内核 —— SiC MOSFET / IGBT 可切换
================================================
工程损耗链Ana：
  1) 导通损耗：SiC = Rds(on)(Tj)·Irms²（Rds 随温度上升）；IGBT = Vce0·Iavg + r_ce·Irms²
  2) 开关损耗：Eon/Eoff 按数据手册参考点缩放
       E(V,I,T) = Eref·(Vdc/Vref)^kv·(I/Iref)^ki·(1+αT·(Tj−Tref))
       IGBT Eoff 温敏更强（拖尾电流），SiC Eoff 温度不敏感
  3) 反向恢复损耗：Err（SiC 很小、IGBT 较大）
  4) 结温闭环迭代：Tj = Ta + P_loss·Rth_total，Rds(on) 依赖 Tj → 迭代收敛
  5) 并联均流：n 并联，电流均分 + 不均衡系数 kimb，最热管电流 = I/n·(1+kimb)
  6) 寿命估算：Coffin-Manson 功率循环 Nf = A·(ΔTj)^(-n)

所有公式集中于此，网页/Excel/复算共用（verify_web.js 逐项比对）。
系数来源：开关损耗缩放指数 kv≈1.2~1.4, ki≈0.8~1.0, αT≈0.002~0.005/K（数据手册工程惯例）；
结温自洽迭代与并联降额参考 Wolfspeed SpeedFit / 通用功率半导体损耗建模方法。
"""
import math

# ==================== 输入区（工程典型值，按实际器件手册核对）====================
DEVICE      = 'SiC'      # 'SiC' 或 'IGBT'
# 工况
VDC         = 800.0      # 直流母线 V
IRMS        = 180.0      # 器件电流 RMS（单相桥臂）A
IAVG        = 120.0      # 器件电流平均 A（IGBT 导通损耗用）
FSW_KHZ     = 10.0       # 开关频率 kHz
DUTY        = 0.5        # 占空比
TA          = 40.0       # 环境温度 °C
# 热阻（结→壳 + 壳→散热器 + 散热器→环境，单管）
RTH_JC      = 0.15       # K/W
RTH_CS      = 0.05       # K/W
RTH_SA      = 0.20       # K/W
# 并联
N_PARALLEL  = 2          # 并联器件数
K_IMBAL     = 0.05       # 电流不均衡系数（最热管 +5%）
# 器件参数 —— SiC MOSFET（1200V/200A 级别工程典型值）
RDS_ON_25   = 8.0        # mΩ @25°C
RDS_TCO     = 0.0045     # Rds(on) 温度系数 /K（近似线性段）
EON_REF     = 1.20       # mJ @Vref/Iref/Tref
EOFF_REF    = 0.80       # mJ
ERR_REF     = 0.25       # mJ 反向恢复
KV          = 1.3        # 电压缩放指数
KI          = 0.9        # 电流缩放指数
ALPHA_T     = 0.002      # 开关损耗温度系数 /K（SiC 小）
TREF        = 25.0       # 参考温度 °C
VREF        = 800.0      # 参考电压 V
IREF        = 200.0      # 参考电流 A
# IGBT 参数（1200V/200A 级别工程典型值）
VCE0        = 0.9        # V 阈值（导通压降截距）
RCE         = 4.0        # mΩ 导通斜率
EON_REF_I   = 3.5        # mJ
EOFF_REF_I  = 4.2        # mJ（拖尾电流大）
ERR_REF_I   = 1.8        # mJ
ALPHA_T_I   = 0.004      # IGBT 开关损耗温敏更强
TJ_MAX      = 150.0      # 结温上限 °C（SiC 常用 150/175，IGBT 150）
DT_LIFE_REF = 80.0       # 寿命参考循环温差 K
NF_REF      = 2e5        # 参考循环次数 @ΔTj=80K
M_COFFIN    = 5.0        # Coffin-Manson 指数
CYC_PER_YR  = 5e5        # 每年功率循环次数（工况相关，估算）


def scale_energy(eref_mJ, Vdc, I, Tj, alpha_t, kv=KV, ki=KI):
    """开关能量缩放：Eref·(Vdc/Vref)^kv·(I/Iref)^ki·(1+αT·(Tj−Tref)) [mJ]"""
    return (eref_mJ * (Vdc/VREF)**kv * (I/IREF)**ki *
            (1 + alpha_t*(Tj - TREF)))


def solve(device=None):
    dev = device or DEVICE
    n = max(1, N_PARALLEL)
    # 最热管电流（并联均分 + 不均衡）
    i_rms_dev = IRMS / n * (1 + K_IMBAL)
    i_avg_dev = IAVG / n * (1 + K_IMBAL)
    rth_total = RTH_JC + RTH_CS + RTH_SA

    # 结温闭环迭代（Rds(on) 随 Tj 上升 → 损耗↑ → Tj↑）
    Tj = TA + 30.0
    for _ in range(60):
        if dev == 'SiC':
            rds = RDS_ON_25*1e-3 * (1 + RDS_TCO*(Tj - 25.0))  # Ω
            p_cond = rds * i_rms_dev**2
            eon = scale_energy(EON_REF, VDC, i_rms_dev, Tj, ALPHA_T)
            eoff = scale_energy(EOFF_REF, VDC, i_rms_dev, Tj, ALPHA_T)
            err = scale_energy(ERR_REF, VDC, i_rms_dev, Tj, 0.0)  # SiC Err 温不敏感
            rds_mohm = rds*1e3
        else:
            p_cond = VCE0*i_avg_dev + RCE*1e-3*i_rms_dev**2
            eon = scale_energy(EON_REF_I, VDC, i_rms_dev, Tj, ALPHA_T_I)
            eoff = scale_energy(EOFF_REF_I, VDC, i_rms_dev, Tj, ALPHA_T_I)
            err = scale_energy(ERR_REF_I, VDC, i_rms_dev, Tj, ALPHA_T_I*0.5)
            rds_mohm = None
        # 开关频率下功率（E in mJ → W: mJ·kHz = W）
        p_sw = (eon + eoff) * FSW_KHZ
        p_rr = err * FSW_KHZ
        p_total = p_cond + p_sw + p_rr
        Tj_new = TA + p_total * rth_total
        if abs(Tj_new - Tj) < 1e-6:
            Tj = Tj_new
            break
        Tj = Tj_new

    # 校核
    margin = TJ_MAX - Tj
    ok_temp = margin > 10.0     # 要求 >10K 裕度
    # 寿命（Coffin-Manson，用结温相对环境的摆幅近似）
    dTj = max(1.0, Tj - TA)
    nf = NF_REF * (DT_LIFE_REF / dTj)**M_COFFIN
    life_yr = nf / CYC_PER_YR

    return dict(
        device=dev, Vdc=VDC, fsw_khz=FSW_KHZ, n_parallel=n,
        i_rms_dev=i_rms_dev, i_avg_dev=i_avg_dev, rth_total=rth_total,
        rds_mohm=rds_mohm, p_cond=p_cond, eon=eon, eoff=eoff, err=err,
        p_sw=p_sw, p_rr=p_rr, p_total=p_total, Tj=Tj, margin=margin,
        ok_temp=ok_temp, dTj=dTj, nf=nf, life_yr=life_yr,
    )


if __name__ == '__main__':
    print("=" * 66)
    print("器件损耗与结温评估")
    print("=" * 66)
    for dev in ['SiC', 'IGBT']:
        r = solve(dev)
        print(f"\n--- {dev} (并联 {r['n_parallel']} 管, fs={r['fsw_khz']:.0f}kHz) ---")
        def s(name, val, unit=''):
            print(f"  {name:22s} {val:12.3f}  {unit}")
        if r['rds_mohm'] is not None:
            s('Rds(on)@Tj', r['rds_mohm'], 'mΩ')
        s('最热管 Irms', r['i_rms_dev'], 'A')
        s('导通损耗 Pcond', r['p_cond'], 'W')
        s('Eon', r['eon'], 'mJ'); s('Eoff', r['eoff'], 'mJ'); s('Err', r['err'], 'mJ')
        s('开关损耗 Psw', r['p_sw'], 'W')
        s('反向恢复 Prr', r['p_rr'], 'W')
        s('总损耗 Ptotal', r['p_total'], 'W')
        s('结温 Tj', r['Tj'], '°C')
        s('裕度 (Tjmax−Tj)', r['margin'], 'K')
        s('寿命估算', r['life_yr'], '年')
        print(f"  结温校核(裕度>10K): {'PASS' if r['ok_temp'] else 'FAIL'}")
