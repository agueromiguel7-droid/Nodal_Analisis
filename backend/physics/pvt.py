import math

def rs_standing(api, sg_gas, p, t):
    """
    Gas Solubility (Rs) - Standing Correlation
    Args:
        api: API gravity of oil
        sg_gas: Speciﬁc gravity of gas
        p: Pressure (psi)
        t: Temperature (°F)
    Returns:
        Rs in SCF/STB
    """
    x = 0.0125 * api - 0.00091 * t
    rs = sg_gas * (((p / 18.2) + 1.4) * (10 ** x)) ** 1.2048
    return max(0, rs)

def bo_standing(api, sg_gas, rs, t):
    """
    Oil Formation Volume Factor (Bo) - Standing Correlation
    """
    sg_oil = 141.5 / (api + 131.5)
    f = rs * math.sqrt(sg_gas / sg_oil) + 1.25 * t
    bo = 0.9759 + 0.00012 * (f ** 1.2)
    return bo

def bg_ideal(p, t_r, p_pc, t_pc):
    """
    Gas Formation Volume Factor (Bg)
    Simplified ideal gas or using Z-factor (Placeholder for complex EOS)
    """
    # Simply using standard Bg = 0.02827 * z * T / P
    z = 0.9 # Placeholder Z factor
    bg = 0.02827 * z * (t_r + 460) / p
    return bg

def mu_o_beggs_robinson(api, t):
    """
    Dead oil viscosity - Beggs & Robinson
    """
    x = (t ** -1.163) * math.exp(6.9824 - 0.04658 * api)
    mu_od = (10 ** x) - 1
    return max(0.1, mu_od)

def mu_o_live_beggs_robinson(mu_od, rs):
    """
    Live oil viscosity - Beggs & Robinson
    """
    a = 10.715 * ((rs + 100) ** -0.515)
    b = 5.44 * ((rs + 150) ** -0.338)
    mu_o = a * (mu_od ** b)
    return mu_o
