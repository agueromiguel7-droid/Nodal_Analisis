import math

def calc_ipr_darcy_oil(k, h, pr, pwf, mu_o, bo, re, rw, s):
    """
    Oil IPR using Darcy's Law for pseudo-steady state radial flow.
    Args:
        k (mD): Permeability
        h (ft): Pay zone thickness
        pr (psi): Reservoir pressure
        pwf (psi): Flowing bottomhole pressure
        mu_o (cp): Oil viscosity
        bo (RB/STB): Oil formation volume factor
        re (ft): Drainage radius
        rw (ft): Wellbore radius
        s: Skin factor
    Returns:
        Qo (STB/d): Oil flow rate
    """
    if pwf > pr:
        return 0.0
    
    denominator = 141.2 * mu_o * bo * (math.log(re / rw) - 0.75 + s)
    if denominator <= 0:
        return 0.0
    
    qo = (k * h * (pr - pwf)) / denominator
    return max(0.0, qo)

def calc_ipr_vogel_oil(q_test, pwf_test, pr, pwf):
    """
    Oil IPR using Vogel's correlation for saturated reservoirs.
    Calculates Qmax from test point, then Q at given Pwf.
    """
    if pwf > pr or pwf_test >= pr:
        return 0.0
        
    term_test = 1 - 0.2 * (pwf_test / pr) - 0.8 * ((pwf_test / pr) ** 2)
    if term_test <= 0: return 0.0
    
    q_max = q_test / term_test
    
    term_target = 1 - 0.2 * (pwf / pr) - 0.8 * ((pwf / pr) ** 2)
    qo = q_max * term_target
    return max(0.0, qo)

def calc_ipr_joshi_horizontal(kh, kv, h, L, pr, pwf, mu, bo, reH, rw, s):
    """
    Horizontal well IPR using Joshi's analytical model.
    """
    if pwf > pr: return 0.0
    
    beta = math.sqrt(kh / kv)
    
    # Calculate major half-axis of drainage ellipse (a)
    term1 = 0.5 * math.sqrt(0.25 + (reH / (L / 2)) ** 4)
    a = (L / 2) * (0.5 + term1) ** 0.5
    
    num = 0.00708 * kh * h * (pr - pwf)
    
    den_part1 = math.log((a + math.sqrt(a**2 - (L/2)**2)) / (L/2))
    den_part2 = (beta * h / L) * math.log((beta * h) / (2 * rw))
    
    den = bo * mu * (den_part1 + den_part2 + s)
    if den <= 0: return 0.0
    
    qo = num / den
    return max(0.0, qo)
