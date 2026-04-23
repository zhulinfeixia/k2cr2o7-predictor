"""
精确的铬物种浓度计算 - 基于化学平衡常数
使用平衡常数公式直接计算，不根据pH分情况
"""

import math


def calculate_chromium_species_exact(C_total, pH, Ka1=2.94e-2, Ka2=1.26e-6):
    """
    精确计算铬物种浓度（基于化学平衡常数）
    
    反应体系：
    1) H2CrO4 ⇌ H+ + HCrO4-     Ka1 = 2.94×10^-2
    2) HCrO4- ⇌ H+ + CrO4^2-    Ka2 = 1.26×10^-6
    3) 2HCrO4- ⇌ Cr2O7^2- + H2O  K_dimer = 10^2.2 = 1.58×10^1
    
    物料平衡：
    C_total = [H2CrO4] + [HCrO4-] + [CrO4^2-] + 2[Cr2O7^2-]
    
    参数：
    - C_total: 总铬浓度 (M)
    - pH: pH 值
    - Ka1: 第一解离常数 = 2.94×10^-2
    - Ka2: 第二解离常数 = 1.26×10^-6
    """
    
    H = 10**(-pH)
    
    # 平衡常数（科学计数法表示）
    Ka1 = 2.94e-2      # H2CrO4 ⇌ H+ + HCrO4-
    Ka2 = 1.26e-6      # HCrO4- ⇌ H+ + CrO4^2-
    K_dimer = 1.58e1   # 2HCrO4- ⇌ Cr2O7^2- + H2O (10^2.2)
    
    # 通过平衡常数建立方程组求解
    # 设 [HCrO4-] = x，则：
    # [Cr2O7^2-] = K_dimer * x^2 / [H2O] ≈ K_dimer * x^2 (水活度≈1)
    # [CrO4^2-] = Ka2 * x / [H+]
    # [H2CrO4] = x * [H+] / Ka1
    
    # 物料平衡方程：
    # C_total = [H2CrO4] + [HCrO4-] + [CrO4^2-] + 2[Cr2O7^2-]
    # C_total = x*[H+]/Ka1 + x + Ka2*x/[H+] + 2*K_dimer*x^2
    
    # 整理为关于 x 的二次方程：a*x^2 + b*x + c = 0
    a = 2 * K_dimer
    b = 1 + H/Ka1 + Ka2/H
    c = -C_total
    
    # 求解二次方程
    discriminant = b**2 - 4*a*c
    if discriminant >= 0:
        x = (-b + math.sqrt(discriminant)) / (2*a)  # [HCrO4-]
    else:
        # 退化为线性方程求解
        x = C_total / b
    
    # 通过平衡常数计算各组分浓度（科学计数法形式）
    HCrO4 = x                                          # [HCrO4-]
    Cr2O7 = K_dimer * x**2                            # [Cr2O7^2-]
    CrO4 = Ka2 * x / H                                # [CrO4^2-]
    H2CrO4 = x * H / Ka1                              # [H2CrO4]
    
    # 归一化确保物料平衡
    total_check = H2CrO4 + HCrO4 + CrO4 + 2*Cr2O7
    
    return {
        'H2CrO4': H2CrO4,
        'HCrO4-': HCrO4,
        'CrO4^2-': CrO4,
        'Cr2O7^2-': Cr2O7,
        'total_check': total_check
    }


def format_scientific(value, unit="M"):
    """将数值格式化为科学计数法字符串"""
    if value == 0:
        return f"0 {unit}"
    exponent = math.floor(math.log10(abs(value)))
    mantissa = value / (10 ** exponent)
    return f"{mantissa:.2f}×10^{exponent} {unit}"


# 测试计算
print("=" * 70)
print("铬物种浓度计算 (基于化学平衡常数)")
print("=" * 70)
print("平衡常数（科学计数法）：")
print("  Ka1 = 2.94×10^-2  (H2CrO4 ⇌ H+ + HCrO4-)")
print("  Ka2 = 1.26×10^-6  (HCrO4- ⇌ H+ + CrO4^2-)")
print("  K_dimer = 1.58×10^1  (2HCrO4- ⇌ Cr2O7^2- + H2O)")
print("=" * 70)

# 示例 1: 0.01 M, pH = 2
print("\n【示例 1】C_total = 0.01 M (10 mM), pH = 2")
print("-" * 50)
result1 = calculate_chromium_species_exact(0.01, 2)
print(f"H2CrO4:     {format_scientific(result1['H2CrO4'])}  ({result1['H2CrO4']/0.01*100:5.2f}%)")
print(f"HCrO4-:     {format_scientific(result1['HCrO4-'])}  ({result1['HCrO4-']/0.01*100:5.2f}%)")
print(f"CrO4^2-:    {format_scientific(result1['CrO4^2-'])}  ({result1['CrO4^2-']/0.01*100:5.2f}%)")
print(f"Cr2O7^2-:   {format_scientific(result1['Cr2O7^2-'])}  ({result1['Cr2O7^2-']/0.01*200:5.2f}%)")
print(f"总铬验证:   {format_scientific(result1['total_check'])}")

# 示例 2: 0.06 M, pH = 10
print("\n【示例 2】C_total = 0.06 M (60 mM), pH = 10")
print("-" * 50)
result2 = calculate_chromium_species_exact(0.06, 10)
print(f"H2CrO4:     {format_scientific(result2['H2CrO4'])}  ({result2['H2CrO4']/0.06*100:5.2f}%)")
print(f"HCrO4-:     {format_scientific(result2['HCrO4-'])}  ({result2['HCrO4-']/0.06*100:5.2f}%)")
print(f"CrO4^2-:    {format_scientific(result2['CrO4^2-'])}  ({result2['CrO4^2-']/0.06*100:5.2f}%)")
print(f"Cr2O7^2-:   {format_scientific(result2['Cr2O7^2-'])}  ({result2['Cr2O7^2-']/0.06*200:5.2f}%)")
print(f"总铬验证:   {format_scientific(result2['total_check'])}")

# 不同 pH 下的 Cr2O7^2- 分布
print("\n" + "=" * 70)
print("不同 pH 下的物种分布 (C_total = 0.01 M)")
print("=" * 70)
print(f"{'pH':>4} | {'[Cr2O7^2-]':>15} | {'[HCrO4-]':>15} | {'[CrO4^2-]':>15} | {'[H2CrO4]':>15}")
print("-" * 70)
for ph in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]:
    r = calculate_chromium_species_exact(0.01, ph)
    print(f"{ph:4d} | {format_scientific(r['Cr2O7^2-'], ''):>15} | {format_scientific(r['HCrO4-'], ''):>15} | {format_scientific(r['CrO4^2-'], ''):>15} | {format_scientific(r['H2CrO4'], ''):>15}")
