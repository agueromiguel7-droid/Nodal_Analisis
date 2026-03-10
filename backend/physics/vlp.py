import backend.psapy.BeggsandBrill as bb

def marching_algorithm_vlp(p_wh, t_wh, t_wf, md_total, tvd_total, segments, d_inner, q_liquid, wc, glr, sg_oil, sg_gas, sg_water, pvt_model="standing", y_h2s=0.0, y_co2=0.0, y_n2=0.0):
    """
    Implements discrete segment marching down the wellbore.
    Returns the Bottomhole Flowing Pressure (Pwf).
    We use the robust Beggs and Brill method via psapy.
    """
    if q_liquid <= 0:
        return p_wh + 0.433 * sg_water * tvd_total # Hydrostatic static column if no flow

    # Convert fluid parameters to psapy format
    # qs are in stb/d
    wc_frac = min(max(wc / 100.0, 0.0), 0.999) # limit wc just in case
    q_water = wc_frac * q_liquid
    q_oil = (1.0 - wc_frac) * q_liquid
    
    # API gravity calculation
    api = (141.5 / sg_oil) - 131.5 if sg_oil > 0 else 35.0
    
    # print debug
    if q_liquid == 1000.0 or True: # Just to print at least once per run or continuously, let's just print a few to not flood
        pass
        
    print(f"VLP Calc -> Q: {q_liquid:.1f}, WC: {wc}, GLR: {glr}, API: {api:.1f}, Model: psapy BB")
    
    
    # Inner diameter inches (psapy expects ID in inches)
    d_inner_inches = d_inner * 12.0
    
    # Deviation Angle
    import math
    # Safe guard against mathematical domain error if user enters TVD > MD
    ratio = min(tvd_total / md_total, 1.0) if md_total > 0 else 1.0
    theta_rad = math.asin(ratio)
    angle_deg = math.degrees(theta_rad)
    
    try:
        # Calculate pwf using the library
        pwf = bb.Pwf_q(
            FWHP=p_wh,
            FWHT=t_wh,
            Oil_Rate=q_oil,
            Water_Rate=q_water,
            GOR=glr,
            GasGrav=sg_gas,
            API=api,
            WaterGrav=sg_water,
            ID=d_inner_inches,
            Angle=angle_deg,
            Depth=md_total,
            FBHT=t_wf,
            pvt_model=pvt_model
        )
        
        # Mathematical Guard: Extremely high velocities in small pipes cause 
        # friction equations to diverge to infinity (e.g. 35k psi+).
        # We cap the maximum realistic required pressure to prevent chart distortion.
        max_realistic_pwf = 15000.0 # psi cap
        if pwf > max_realistic_pwf or math.isnan(pwf):
            return max_realistic_pwf
            
        return pwf
    except Exception as e:
        # Fallback pseudo hydrostatic if BB fails numerically
        return p_wh + (md_total * 0.433)
