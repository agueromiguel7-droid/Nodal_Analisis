import numpy as np
from backend.physics.ipr import calc_ipr_darcy_oil, calc_ipr_joshi_horizontal, calc_ipr_vogel_oil
from backend.physics.vlp import marching_algorithm_vlp

def find_operating_point(ipr_func, vlp_func, min_q=0, max_q=10000, points=50):
    """
    Finds the intersection point between IPR and VLP curves.
    Args:
        ipr_func: Function returning Qo given Pwf
        vlp_func: Function returning Pwf given Qo
    Returns:
        dict: containing arrays for IPR, VLP and intersection point (Q_opt, Pwf_opt)
    """
    
    # Generate Q array
    q_array = np.linspace(min_q, max_q, points)
    
    ipr_pwf = []
    vlp_pwf = []
    
    # Calculate IPR (Inflow) and VLP (Outflow)
    for q in q_array:
        # Pwf from IPR: Inverse function needed usually but for now placeholder:
        # Assuming ipr_func returns Qo for a Pwf, here we need Pwf for a Qo.
        # This requires numerical root finding on IPR for Pwf(Qo).
        
        # Simplified: Using VLP to generate Pwf directly
        pwf_outFlow = vlp_func(q)
        vlp_pwf.append(pwf_outFlow)
        
        # We need an inverse IPR solver here. For prototype, we generate IPR values differently.
        
    return {
        "q_array": q_array.tolist(),
        "vlp_pwf": vlp_pwf,
        "operating_point": None # Placeholder for intersection
    }

def generate_nodal_curves(well_params, vlp_params, model_type="darcy_radial"):
    """
    Generates both curves based on input parameters.
    Returns JSON structure for frontend plotting.
    """
    # 1. Generate IPR curve (Pwf vs Q)
    # Using np.linspace for Pwf from Pr down to 0
    pr = well_params.get("reservior_pressure", 4000)
    pwf_array = np.linspace(pr, 0, 50)
    ipr_q = []
    
    for pwf in pwf_array:
        if model_type == "darcy_radial":
           q = calc_ipr_darcy_oil(
               well_params.get("k", 50),
               well_params.get("h", 100),
               pr,
               pwf,
               well_params.get("mu_o", 2.0),
               well_params.get("bo", 1.2),
               well_params.get("re", 1500),
               well_params.get("rw", 0.3),
               well_params.get("skin", 0)
           )
           ipr_q.append(q)
        elif model_type == "vogel":
           # Assume a synthetic test point around 30% drawdown
           test_pwf = pr * 0.7
           test_q = calc_ipr_darcy_oil(
               well_params.get("k", 50),
               well_params.get("h", 100),
               pr,
               test_pwf,
               well_params.get("mu_o", 2.0),
               well_params.get("bo", 1.2),
               well_params.get("re", 1500),
               well_params.get("rw", 0.3),
               well_params.get("skin", 0)
           )
           q = calc_ipr_vogel_oil(test_q, test_pwf, pr, pwf)
           ipr_q.append(q)
        elif model_type == "joshi":
           q = calc_ipr_joshi_horizontal(
               kh=well_params.get("k", 50),
               kv=well_params.get("k", 50) * 0.1, # assumed 10% vertical
               h=well_params.get("h", 100),
               L=well_params.get("h", 100) * 10,  # assumed 1000ft lateral
               pr=pr,
               pwf=pwf,
               mu=well_params.get("mu_o", 2.0),
               bo=well_params.get("bo", 1.2),
               reH=well_params.get("re", 1500),
               rw=well_params.get("rw", 0.3),
               s=well_params.get("skin", 0)
           )
           ipr_q.append(q)
           
    # 2. Generate VLP curve 
    vlp_q = ipr_q # Evaluate VLP at same Q points for interception
    vlp_pwf = []
    
    # We pass the VLP correlation model to the engine
    vlp_model = vlp_params.get("model", "beggs_brill")
    pvt_model = vlp_params.get("pvt_model", "standing")
    
    for q in vlp_q:
         # Note: For now, Hagedorn & Brown relies on Beggs & Brill physically
         # because psapy internally provides Beggs and Brill but we will expand
         # to native hagedorn algorithms soon. 
         pwf_vlp = marching_algorithm_vlp(
             p_wh=vlp_params.get("p_wh", 500),
             t_wh=vlp_params.get("t_wh", 100),
             t_wf=vlp_params.get("t_wf", 180),
             md_total=vlp_params.get("md_total", 8000),
             tvd_total=vlp_params.get("tvd_total", 8000),
             segments=50,
             d_inner=vlp_params.get("d_inner", 0.33),
             q_liquid=q,
             wc=vlp_params.get("wc", 0),
             glr=vlp_params.get("glr", 300),
             sg_oil=vlp_params.get("sg_oil", 0.85),
             sg_gas=vlp_params.get("sg_gas", 0.65),
             sg_water=vlp_params.get("sg_water", 1.05),
             y_h2s=vlp_params.get("y_h2s", 0.0),
             y_co2=vlp_params.get("y_co2", 0.0),
             y_n2=vlp_params.get("y_n2", 0.0),
             pvt_model=pvt_model
         )
         vlp_pwf.append(pwf_vlp)
         
    # Despike VLP: Remove numerical artifacts from correlation flow regime jumps
    smoothed_vlp_pwf = []
    for i in range(len(vlp_pwf)):
        if i == 0:
            smoothed_vlp_pwf.append(vlp_pwf[i])
        else:
            prev_pwf = smoothed_vlp_pwf[i-1]
            curr_pwf = vlp_pwf[i]
            # If the pressure jumps wildly (> 50% variance) relative to the previous point, 
            # we consider it a correlation boundary artifact if it's abnormally high.
            if curr_pwf > prev_pwf * 1.5 and curr_pwf > 3000:
                # Cap the spike to a slight linear increase from previous point
                curr_pwf = prev_pwf * 1.05 
            smoothed_vlp_pwf.append(curr_pwf)
            
    vlp_pwf = smoothed_vlp_pwf
         
    # Find Intersection
    q_opt = None
    pwf_opt = None
    
    if len(ipr_q) > 0 and len(vlp_pwf) > 0:
        # Interpolate the intersection accurately.
        # VLP can cross IPR twice (unstable region vs stable region). 
        # We want the stable intersection (highest Q where VLP goes above IPR).
        # We search from right to left (highest Q to lowest Q)
        for i in range(len(ipr_q) - 2, 0, -1):
            ipr1, ipr2 = pwf_array[i], pwf_array[i+1]
            vlp1, vlp2 = vlp_pwf[i], vlp_pwf[i+1]
            q1, q2 = ipr_q[i], ipr_q[i+1]
            
            # Check for crossing between point i and i+1
            if (vlp1 - ipr1) * (vlp2 - ipr2) <= 0:
                # Linear interpolation for exact intersection:
                # y - y1 = m(x - x1)
                # IPR: y = m_ipr * (x - q1) + ipr1
                # VLP: y = m_vlp * (x - q1) + vlp1
                # (m_ipr - m_vlp) * (x - q1) = vlp1 - ipr1
                
                m_ipr = (ipr2 - ipr1) / (q2 - q1) if q2 != q1 else 0
                m_vlp = (vlp2 - vlp1) / (q2 - q1) if q2 != q1 else 0
                
                if m_ipr != m_vlp:
                    dq = (vlp1 - ipr1) / (m_ipr - m_vlp)
                    q_opt = q1 + dq
                    pwf_opt = ipr1 + m_ipr * dq
                     
                    # Validation: True operating points should have positive rate and pressure
                    if q_opt > 0 and pwf_opt > 0:
                        break # Found the highest valid Q intersection
        
        # If no strict crossing was found, but the curves are very close (e.g. at the edge of natural flow),
        # or if the well is dead (VLP always > IPR), we leave it as None (0).
            
    return {
        "ipr": { "q": ipr_q, "pwf": pwf_array.tolist() },
        "vlp": { "q": vlp_q, "pwf": vlp_pwf },
        "intersection": { "q": q_opt, "pwf": pwf_opt }
    }

def generate_wc_sensitivity(well_params, vlp_params, model_type="darcy_radial", wc_list=[0, 15, 30, 50, 75]):
    """
    Runs the Nodal analysis over an array of Water Cuts (WC%) and extracts the operating points.
    Returns a list of dictionaries suitable for plotting a sensitivity dataframe.
    """
    import copy
    results = []
    
    for wc in wc_list:
        # Create a deep copy to isolate this run
        sim_vlp_params = copy.deepcopy(vlp_params)
        sim_vlp_params["wc"] = float(wc)
        
        # Calculate full curves for this WC
        sim_data = generate_nodal_curves(well_params, sim_vlp_params, model_type=model_type)
        intersection = sim_data.get("intersection")
        
        if intersection and intersection.get("q"):
            op_q = intersection["q"]
            op_pwf = intersection["pwf"]
            
            # Calculate phase flowrates based on the WC
            wc_frac = wc / 100.0
            q_water = op_q * wc_frac
            q_oil = op_q * (1.0 - wc_frac)
            
            # Estimate gas rate using GOR/GLR
            glr = sim_vlp_params.get("glr", 0) # SCF/STB of liquid
            q_gas_mscfd = (op_q * glr) / 1000.0
            
            status = "✅" if op_pwf > sim_vlp_params.get("p_wh", 0) else "⚠️"
            if op_q < 500: status = "🔴"
            
            # If this is the current active model highlight it
            is_active = " (Actual)" if float(wc) == float(vlp_params.get("wc", 0)) else ""
            
            results.append({
                "Corte de Agua (%)": f"{wc}%{is_active}",
                "Presión Operación (psia)": f"{op_pwf:,.0f}",
                "Tasa Operación Líquido (STB/D)": f"{op_q:,.0f}",
                "Tasa Petróleo (STB/D)": f"{q_oil:,.0f}",
                "Tasa Gas (MSCF/D)": f"{q_gas_mscfd:,.0f}",
                "Estado": status
            })
        else:
            is_active = " (Actual)" if float(wc) == float(vlp_params.get("wc", 0)) else ""
            results.append({
                "Corte de Agua (%)": f"{wc}%{is_active}",
                "Presión Operación (psia)": "-",
                "Tasa Operación Líquido (STB/D)": "-",
                "Tasa Petróleo (STB/D)": "-",
                "Tasa Gas (MSCF/D)": "-",
                "Estado": "🔴"
            })
            
    return results
