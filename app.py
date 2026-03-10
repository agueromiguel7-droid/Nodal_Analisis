import streamlit as st
import streamlit.components.v1 as components
import json
import os
from auth import check_password
from ui_components import render_stitch_html, well_analysis_component
from backend.physics.nodal_solver import generate_nodal_curves, generate_wc_sensitivity

st.set_page_config(
    page_title="Nodal Analysis Pro",
    page_icon="🛢️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Standardized API 5CT Tubing Sizes (Outer Diameter -> Internal Diameter)
API_5CT_TUBING = {
    "2 3/8\" OD (1.995\" ID)": 1.995,
    "2 7/8\" OD (2.441\" ID)": 2.441,
    "3 1/2\" OD (2.992\" ID)": 2.992,
    "4\" OD   (3.476\" ID)": 3.476,
    "4 1/2\" OD (3.958\" ID)": 3.958,
    "5\" OD   (4.408\" ID)": 4.408,
    "5 1/2\" OD (4.892\" ID)": 4.892
}

# Authentication check
if not check_password():
    st.stop()
    
# CSS block removed to restore Streamlit standard margins

# Initialization of global state and language
if "lang" not in st.session_state:
    st.session_state["lang"] = "es"

if "well_state" not in st.session_state:
    st.session_state["well_state"] = {
        "md_total": 8000.0,
        "tvd_total": 8500.0,
        "d_inner": 2.992
    }

TEXTS = {
    "nav_header": {"es": "Navegación Tectónica", "en": "Tectonic Navigation"},
    "dash": {"es": "Tablero", "en": "Dashboard"},
    "well_analysis": {"es": "Análisis de Pozos", "en": "Well Analysis"},
    "wellbore": {"es": "Esquema del Pozo", "en": "Well Configuration"},
    "sim": {"es": "Simulaciones", "en": "Simulations"},
    "report": {"es": "Reportes", "en": "Reports"},
    "lang_picker": {"es": "Idioma / Language", "en": "Language / Idioma"},
    "pvt_data": {"es": "Entrada de Datos PVT", "en": "PVT Data Input"},
    "res_data": {"es": "Parámetros del Pozo y Tubería (Completación)", "en": "Well & Pipeline Parameters (Completion)"},
    "res_ipr": {"es": "Datos del Yacimiento e IPR", "en": "Reservoir & IPR Data"},
    "res_vlp": {"es": "Datos de Tubería y Trayectoria (VLP)", "en": "Pipeline & Trajectory Data (VLP)"},
    "impurities": {"es": "Impurezas del Gas (Fracciones Molares)", "en": "Gas Impurities (Molar Fractions)"},
    "run_btn": {"es": "Ejecutar Análisis", "en": "Run Analysis"},
    "pvt_rec": {"es": "Recomendación PVT Automática:", "en": "Automatic PVT Recommendation:"},
    "op_point": {"es": "Resultados: Punto de Operación", "en": "Results: Operating Point"},
    "no_flow": {"es": "No se encontró intersección válida (el pozo no fluye bajo estas condiciones).", "en": "No valid intersection found (the well does not flow)."},
    "well_desc": {"es": "Defina las propiedades mecánicas y componentes de fondo para el cálculo nodal.", "en": "Define downhole mechanical properties and components for nodal calculation."},
    "live_schematic": {"es": "Esquema en Vivo", "en": "Live Schematic"},
    "nodal_title": {"es": "Análisis Nodal (IPR vs VLP)", "en": "Nodal Analysis (IPR vs VLP)"}
}

def _(k):
    return TEXTS.get(k, {}).get(st.session_state["lang"], k)

st.sidebar.markdown(f"**{_('lang_picker')}**")
lang_choice = st.sidebar.radio("lang", ["ES", "EN"], index=0 if st.session_state["lang"] == "es" else 1, horizontal=True, label_visibility="collapsed")
st.session_state["lang"] = lang_choice.lower()

st.sidebar.divider()

# Select screen to view
page_keys = ["dash", "well_analysis", "wellbore", "sim", "report"]
if "nav" not in st.session_state:
    st.session_state["nav"] = 1 # well analysis default

page_sel_key = st.sidebar.selectbox(
    _("nav_header"), 
    options=page_keys, 
    index=st.session_state["nav"],
    format_func=lambda k: _(k),
    key="nav_selectbox",
    on_change=lambda: st.session_state.update({"nav": page_keys.index(st.session_state.nav_selectbox)})
)

page_map = {
    "dash": "Tablero",
    "well_analysis": "Análisis de Pozo",
    "wellbore": "Esquema del Pozo",
    "sim": "Simulaciones",
    "report": "Reporte Técnico"
}
page = page_map[page_sel_key]

# Render chosen HTML from stitch_preview folder
html_map = {
    "Tablero": "stitch_preview/dashboard.html",
    "Análisis de Pozo": "stitch_preview/well_analysis.html", # This entry will be ignored for "Análisis de Pozo" page
    "Esquema del Pozo": "stitch_preview/wellbore_schematic.html",
    "Simulaciones": "stitch_preview/simulations.html",
    "Reporte Técnico": "stitch_preview/technical_report.html"
}

# Plot initialization
if "plot_data" not in st.session_state:
    st.session_state["plot_data"] = None

# Example of backend communication for Nodal Analysis logic
if page == "Análisis de Pozo":
    st.markdown("""
    <style>
    div[data-testid="stForm"] {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 1rem;
        padding: 1rem;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }
    html[data-theme="dark"] div[data-testid="stForm"] {
        background-color: #0f172a;
        border-color: #1e293b;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown(f'<h2 style="color: #4f1dd7; font-weight: 700;">{_("nodal_title")}</h2>', unsafe_allow_html=True)
    
    # We use native Streamlit columns to replicate the layout
    col1, col2 = st.columns([1, 2.5], gap="large")
    
    with col1:
        st.subheader(_("pvt_data"))
        
        st.markdown(f'<div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 1rem; padding: 1rem; margin-bottom: 2rem;">', unsafe_allow_html=True)
        cola, colb = st.columns(2)
        with cola:
            rga = st.number_input("RGA (SCF/STB)", value=1200.0, step=10.0)
            wc = st.number_input("Corte de Agua (%)", value=20.0, step=1.0)
            t_wf = st.number_input("Temperatura Fondo (°F)", value=180.0, step=5.0)
        with colb:
            api = st.number_input("Gravedad API", value=26.0, step=1.0)
            sggas = st.number_input("Gravedad Específica Gas", value=0.650, step=0.01)
            salinity = st.number_input("Salinidad Agua (ppm)", value=20000.0, step=1000.0)
            
        st.divider()
        
        ipr_model = st.selectbox("Modelo IPR", ["Darcy (Productividad Constante)", "Vogel (Saturado)", "Joshi (Horizontal)"])
        vlp_model = st.selectbox("Correlación VLP", ["Beggs & Brill", "Hagedorn & Brown", "Genérico"])
        pvt_model = st.selectbox("Correlación PVT", ["Standing (Recomendada)", "Glaso", "Vasquez-Beggs"])
        st.markdown('</div>', unsafe_allow_html=True)
            
        with st.expander(_("res_data"), expanded=False):
            tab_ipr, tab_vlp = st.tabs([_("res_ipr"), _("res_vlp")])
            
            with tab_ipr:
                col_i1, col_i2 = st.columns(2)
                with col_i1:
                    pr = st.number_input("Presión de Yacimiento Pr (psi)", value=4000.0, step=100.0)
                    h = st.number_input("Espesor h (ft)", value=100.0, step=10.0)
                    rw = st.number_input("Radio del Pozo rw (ft)", value=0.3, step=0.05)
                    c_bp = st.number_input("Constante C (Backpressure)", value=0.01, step=0.001, format="%.3f")
                with col_i2:
                    k = st.number_input("Permeabilidad k (mD)", value=50.0, step=10.0)
                    re = st.number_input("Radio de Drenaje re (ft)", value=1500.0, step=100.0)
                    skin = st.number_input("Daño (Skin)", value=0.0, step=0.5)

            with tab_vlp:
                col_v1, col_v2 = st.columns(2)
                with col_v1:
                    p_wh = st.number_input("Presión de Cabezal Pwh (psi)", value=500.0, step=50.0)
                    
                    # API 5CT Mapping logic
                    current_id = float(st.session_state["well_state"]["d_inner"])
                    try:
                        default_idx = list(API_5CT_TUBING.values()).index(current_id)
                    except ValueError:
                        default_idx = 1 # Fallback 2.441
                        
                    d_inner_label = st.selectbox("API 5CT Tubing", options=list(API_5CT_TUBING.keys()), index=default_idx)
                    d_inner = API_5CT_TUBING[d_inner_label]
                    
                    tvd_total = st.number_input("Profundidad TVD (ft)", value=float(st.session_state["well_state"]["tvd_total"]), step=100.0)
                with col_v2:
                    t_wh = st.number_input("Temp. de Cabezal Twh (°F)", value=100.0, step=5.0)
                    md_total = st.number_input("Profundidad MD (ft)", value=float(st.session_state["well_state"]["md_total"]), step=100.0)
                
                # Sync back to global state
                st.session_state["well_state"]["d_inner"] = d_inner
                st.session_state["well_state"]["md_total"] = md_total
                st.session_state["well_state"]["tvd_total"] = tvd_total
                
                st.divider()
                st.markdown(f"**{_('impurities')}**")
                col_imp1, col_imp2, col_imp3 = st.columns(3)
                with col_imp1: y_h2s = st.number_input("H2S", value=0.0, step=0.01, format="%.3f")
                with col_imp2: y_co2 = st.number_input("CO2", value=0.0, step=0.01, format="%.3f")
                with col_imp3: y_n2 = st.number_input("N2", value=0.0, step=0.01, format="%.3f")
            
            well_params = {
                "reservior_pressure": pr,
                "k": k,
                "h": h,
                "re": re, "rw": rw, "skin": skin, "c_bp": c_bp, "mu_o": 2.0, "bo": 1.2
            }
            vlp_params = {
                "p_wh": p_wh,
                "md_total": md_total, "tvd_total": tvd_total, "t_wh": t_wh, "t_wf": t_wf, 
                "d_inner": d_inner / 12.0, # backend expects feet internally for psapy compat initially but Beggs Brill in psapy later takes inches, let's keep it as D_inner/12 or D_inner directly. Looking at `vlp.py` line 29: d_inner_inches = d_inner * 12.0. So the UI needs to provide it in feet to VLP, which then multiplies by 12. So UI is in inches, backend in feet. `d_inner / 12.0`
                "wc": wc, "glr": rga, "sg_gas": sggas, 
                "sg_oil": 141.5 / (api + 131.5) if api else 0.85,
                "sg_water": 1.05,
                "y_h2s": y_h2s, "y_co2": y_co2, "y_n2": y_n2
            }

    with col2:
        col_btn1, col_btn2 = st.columns([3, 1])
        with col_btn2:
            st.markdown("<br>", unsafe_allow_html=True) # visual spacer to align with top
            manual_run = st.button("🚀 " + _("run_btn"), use_container_width=True, type="primary")

        # Always calculate on UI change (Streamlit rerun) or Manual Run click
        # Override calculation parameters with UI inputs
        vlp_params["glr"] = float(rga)
        vlp_params["wc"] = float(wc)
        vlp_params["sg_gas"] = float(sggas)
        vlp_params["t_wf"] = float(t_wf)
        # Dictionaries are correctly populated now from the UI forms directly
        
        if api > 0:
            vlp_params["sg_oil"] = 141.5 / (api + 131.5)
            
        # Calculate Water SG from Salinity input (ppm into wt% TDS)
        tds_wt_pct = float(salinity) / 10000.0
        rho_water = 62.368 + 0.438603 * tds_wt_pct + 0.00160074 * (tds_wt_pct ** 2)
        vlp_params["sg_water"] = float(rho_water / 62.368)
                
        # Map UI strings to backend keys
        ipr_key = "darcy_radial"
        if "Vogel" in ipr_model: ipr_key = "vogel"
        elif "Joshi" in ipr_model: ipr_key = "joshi"
        
        vlp_key = "beggs_brill"
        if "Hagedorn" in vlp_model: vlp_key = "hagedorn_brown"
        elif "Genérico" in vlp_model: vlp_key = "generic"
        
        pvt_key = "standing"
        if "Glaso" in pvt_model: pvt_key = "glaso"
        elif "Vasquez" in pvt_model: pvt_key = "vasquez_beggs"
        
        vlp_params["model"] = vlp_key
        vlp_params["pvt_model"] = pvt_key
        
        st.session_state["well_params"] = well_params
        st.session_state["vlp_params"] = vlp_params
        st.session_state["ipr_key"] = ipr_key
        
        st.session_state["plot_data"] = generate_nodal_curves(well_params, vlp_params, model_type=ipr_key)
            
        # Draw the plot natively using Streamlit Plotly
        data = st.session_state["plot_data"]
        
        # Recommendations System
        with st.expander("🤖 Asistente de Modelado Analítico", expanded=True):
            # PVT Recommendation
            pvt_rec = "💡 **Recomendación PVT:** "
            if api < 30:
                pvt_rec += "Para crudos pesados o medios (API < 30), **Standing** es altamente recomendada." 
            elif api > 40:
                pvt_rec += "Para crudos volátiles (API > 40), **Glaso** ajusta mejor el punto de burbuja."
            else:
                pvt_rec += "Para crudos de gravedad intermedia (30-40 API), **Vasquez-Beggs** ofrece mayor precisión."
            st.info(pvt_rec)
            
            # IPR Recommendation
            if "Vogel" in ipr_model:
                ipr_rec = "💡 **Recomendación IPR:** Has seleccionado **Vogel**, ideal si la presión de fondo fluyente (Pwf) cae por debajo del punto de burbuja (flujo bifásico en el yacimiento)."
            elif "Joshi" in ipr_model:
                ipr_rec = "💡 **Recomendación IPR:** Has seleccionado **Joshi**, el estándar de la industria para modelar pozos con tramos de completación horizontales."
            else:
                ipr_rec = "💡 **Recomendación IPR:** El modelo de **Darcy** es excelente para flujo lineal/radial de un solo líquido (por encima del punto de burbuja)."
            st.success(ipr_rec)
                
            # VLP Recommendation
            if "Hagedorn" in vlp_model:
                 vlp_rec = "💡 **Recomendación VLP:** **Hagedorn & Brown** es un modelo sólido para pozos verticalmente estrictos, especialmente en regímenes de flujo burbuja o tapón."
            else:
                 vlp_rec = "💡 **Recomendación VLP:** **Beggs & Brill** es la correlación más robusta y versátil moderna, capaz de adaptarse a trayectorias desviadas e identificar regímenes de flujo cruzados."
            st.warning(vlp_rec)
        
        if data and data.get("ipr") and data.get("vlp"):
            import plotly.graph_objects as go
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(x=data["ipr"]["q"], y=data["ipr"]["pwf"], mode='lines', 
                                     name='Curva IPR', line={"color": '#4f1dd7', "width": 3}))
            fig.add_trace(go.Scatter(x=data["vlp"]["q"], y=data["vlp"]["pwf"], mode='lines', 
                                     name='Curva VLP', line={"color": '#ef4444', "width": 3}))
            
            if data.get("intersection") and data["intersection"]["q"] is not None:
                fig.add_trace(go.Scatter(
                    x=[data["intersection"]["q"]], 
                    y=[data["intersection"]["pwf"]],
                    mode='markers',
                    name='Punto Operación',
                    marker={"size": 12, "color": '#10b981', "symbol": 'star'},
                    hovertemplate='Q: %{x:.2f} STB/D<br>Pwf: %{y:.2f} psi<extra></extra>'
                ))
                
            fig.update_layout(
                title='Análisis Nodal (IPR vs VLP)',
                xaxis_title='Caudal (STB/D)',
                yaxis_title='Presión de Fondo Fluyente (Pwf - psi)',
                height=500,
                margin={"l": 40, "r": 40, "t": 40, "b": 40},
                legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
                annotations=[
                    dict(
                        x=0.99,
                        y=0.95,
                        xref="paper",
                        yref="paper",
                        text=f"<b>Modelos Activos:</b><br>IPR: {ipr_model}<br>VLP: {vlp_model}<br>PVT: {pvt_model}",
                        showarrow=False,
                        align="right",
                        bgcolor="rgba(255, 255, 255, 0.8)",
                        bordercolor="#cbd5e1",
                        borderwidth=1,
                        borderpad=4,
                        font={"size": 11, "color": "#334155"}
                    )
                ]
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Display Numeric Results explicitly
            if data.get("intersection") and data["intersection"]["q"] is not None:
                st.markdown(f'<h4 style="color: #4f1dd7; margin-top: 1rem;">{_("op_point")}</h4>', unsafe_allow_html=True)
                rc1, rc2, rc3 = st.columns(3)
                rc1.metric(label="Qo", value=f"{data['intersection']['q']:.1f} STB/D")
                rc2.metric(label="Pwf", value=f"{data['intersection']['pwf']:.1f} psi")
                num_points = len(data["ipr"]["q"])
                rc3.metric(label="Resolution", value=f"{num_points} nodos")
            else:
                st.warning(f"⚠️ {_('no_flow')}")
                
            # --- Sensibilidad de Corte de Agua (Water Cut Table) ---
            st.markdown(f'<h4 style="color: #334155; margin-top: 2rem; font-size: 1.1rem;">Análisis de Sensibilidad: Variación de Corte de Agua</h4>', unsafe_allow_html=True)
            
            with st.spinner("Calculando sensibilidades..." if st.session_state["lang"] == "es" else "Calculating sensitivities..."):
                sens_data = generate_wc_sensitivity(well_params, vlp_params, model_type=ipr_key, wc_list=[0, 15, 30, 50, 75])
                
                # Render using Streamlit's native dataframe which is highly interactive and aesthetic
                st.dataframe(
                    sens_data,
                    use_container_width=True,
                    hide_index=True
                )

elif page == "Esquema del Pozo":
    st.markdown(f'<h2 style="color: #4f1dd7; font-weight: 700;">{_("wellbore")}</h2>', unsafe_allow_html=True)
    st.markdown(_("well_desc"))
    
    col1, col2 = st.columns([2.5, 1], gap="large")
    with col1:
        tabs = st.tabs(["Casing", "Tubing", "Perforaciones", "Completación"])
        
        with tabs[0]:
            st.subheader("Sarta de Revestimiento (Casing)")
            c1, c2, c3, c4 = st.columns(4)
            c1.number_input("Prof. Superior (ft)", value=0)
            c2.number_input("Prof. Inferior (ft)", value=8500)
            c3.number_input("DI (pulgadas)", value=6.276)
            c4.number_input("Rugosidad", value=0.0006, format="%.4f")
            
        with tabs[1]:
            st.subheader("Sarta de Producción (Tubing)")
            t1, t2, t3 = st.columns(3)
            md_tubing = t1.number_input("Longitud (ft)", value=float(st.session_state["well_state"]["md_total"]), step=100.0)
            
            # API 5CT mapping
            current_id = float(st.session_state["well_state"]["d_inner"])
            try:
                default_idx = list(API_5CT_TUBING.values()).index(current_id)
            except ValueError:
                default_idx = 1
                
            di_tubing_label = t2.selectbox("API 5CT Tubing - Sync", options=list(API_5CT_TUBING.keys()), index=default_idx)
            di_tubing = API_5CT_TUBING[di_tubing_label]
            
            t3.number_input("Rugosidad Tubería", value=0.0006, format="%.4f")
            
            st.session_state["well_state"]["md_total"] = md_tubing
            st.session_state["well_state"]["d_inner"] = di_tubing
            
        with tabs[2]:
            st.subheader("Intervalos de Perforación")
            p1, p2 = st.columns(2)
            p1.number_input("Tope (ft)", value=8350)
            p2.number_input("Base (ft)", value=8400)
            
        with tabs[3]:
            st.subheader("Equipos y Completación")
            st.info("Bomba Electrosumergible (ESP) - Profundidad: 7800 ft")
            st.info("Empacadura (Packer) - Asentada a 8150 ft MD")
            
    with col2:
        st.subheader(_("live_schematic"))
        import plotly.graph_objects as go
        fig = go.Figure()
        
        # Draw casing
        fig.add_shape(type="rect", x0=-3.5, x1=3.5, y0=0, y1=-8500, line={"color": "gray", "width": 2}, fillcolor="lightgray", opacity=0.3)
        # Draw tubing
        fig.add_shape(type="rect", x0=-1.5, x1=1.5, y0=0, y1=-st.session_state["well_state"]["md_total"], line={"color": "#4f1dd7", "width": 2}, fillcolor="#4f1dd7", opacity=0.4)
        # Draw Packer
        fig.add_shape(type="rect", x0=-3.5, x1=3.5, y0=-8140, y1=-8160, line={"color": "black", "width": 2}, fillcolor="#1e293b")
        
        # Text Annotations inside the plot
        fig.add_annotation(x=4, y=-8150, text="Packer", showarrow=False, xanchor="left", font={"color": "#1e293b", "size": 10})
        fig.add_annotation(x=4, y=-7800, text="ESP", showarrow=False, xanchor="left", font={"color": "#ef4444", "size": 10})
        
        # Draw ESP
        fig.add_shape(type="rect", x0=-1.5, x1=1.5, y0=-7780, y1=-7820, line={"color": "white", "width": 1}, fillcolor="#ef4444")
        
        fig.update_layout(
             yaxis={"title": "TVD (ft)", "dtick": 1000},
             xaxis=dict(visible=False, range=[-5, 5]),
             height=600,
             margin=dict(l=20, r=20, t=40, b=20),
             paper_bgcolor='rgba(0,0,0,0)',
             plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)

elif page == "Simulaciones":
    st.markdown(f'<h2 style="color: #4f1dd7; font-weight: 700;">Simulaciones Sensibles</h2>', unsafe_allow_html=True)
    st.markdown("Sensibilidad multiparamétrica del modelo Nodal activo.")
    
    if st.session_state.get("plot_data") and st.session_state["plot_data"].get("intersection"):
        data = st.session_state["plot_data"]
        op = data["intersection"]
        
        # Top KPI Cards
        st.markdown('<div style="padding: 1rem; border-radius: 0.5rem; background-color: rgba(79, 29, 215, 0.05); border: 1px solid rgba(79, 29, 215, 0.1); margin-bottom: 2rem;">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        col1.metric("Pwf Actual", f"{op['pwf']:.1f} psia")
        col2.metric("Qo Actual", f"{op['q']:.1f} STB/d")
        col3.metric("AOF Est.", f"{max(data['ipr']['q']):.1f} STB/d")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Sensitivity options
        st.subheader("Configuración de Sensibilidad")
        sens_param = st.selectbox("Parámetro a sensibilizar", ["Diámetro de Tubería (API 5CT)", "Presión de Cabezal (Pwh)"])
        
        if sens_param == "Diámetro de Tubería (API 5CT)":
            st.info("La sensibilidad de tubería permite visualizar múltiples curvas VLP intersectando la curva IPR actual.")
            selected_ods = st.multiselect("Seleccionar Diámetros (OD)", list(API_5CT_TUBING.keys()), default=[list(API_5CT_TUBING.keys())[1], list(API_5CT_TUBING.keys())[3]])
            
            if st.button("Ejecutar Sensibilidad VLP", type="primary"):
                with st.spinner("Simulando cruces VLP..."):
                    import plotly.graph_objects as go
                    import copy
                    
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=data["ipr"]["q"], y=data["ipr"]["pwf"], mode='lines', name='Curva IPR Base', line={"color": '#4f1dd7', "width": 4}))
                    
                    w_params = st.session_state["well_params"]
                    v_params = st.session_state["vlp_params"]
                    current_ipr_key = st.session_state.get("ipr_key", "darcy_radial")
                    
                    colors = ['#ef4444', '#f59e0b', '#10b981', '#3b82f6', '#8b5cf6']
                    
                    for idx, od in enumerate(selected_ods):
                        sim_vlp = copy.deepcopy(v_params)
                        sim_vlp["d_inner"] = API_5CT_TUBING[od] / 12.0 # convert inches to feet for backend
                        
                        sim_data = generate_nodal_curves(w_params, sim_vlp, model_type=current_ipr_key)
                        
                        c = colors[idx % len(colors)]
                        fig.add_trace(go.Scatter(x=sim_data["vlp"]["q"], y=sim_data["vlp"]["pwf"], mode='lines', name=f'VLP {od}', line={"color": c, "width": 2}))
                        
                        if sim_data.get("intersection") and sim_data["intersection"]["q"]:
                            fig.add_trace(go.Scatter(
                                x=[sim_data["intersection"]["q"]], 
                                y=[sim_data["intersection"]["pwf"]],
                                mode='markers',
                                showlegend=False,
                                marker={"size": 10, "color": c, "symbol": 'circle'},
                                hovertemplate=f'{od}<br>Q: %{{x:.2f}}<br>Pwf: %{{y:.2f}}<extra></extra>'
                            ))
                            
                    st.success("Sensibilidad calculada exitosamente.")
                    fig.update_layout(
                        title="Sensibilidad de Tubería de Producción vs IPR", 
                        xaxis_title="Caudal (STB/D)", 
                        yaxis_title="Presión de Fondo (psia)",
                        height=600,
                        margin=dict(l=40, r=40, t=60, b=40),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
        elif sens_param == "Presión de Cabezal (Pwh)":
             st.info("La sensibilidad variando la presión en el cabezal simula escenarios de diferentes contrapresiones en superficie (e.g., choke, separador).")
             base_pwh = st.session_state["vlp_params"]["p_wh"]
             pwh_arr_input = st.text_input("Presiones a Simular (separadas por coma)", f"200, {int(base_pwh)}, 800, 1000")
             
             if st.button("Ejecutar Sensibilidad Pwh", type="primary"):
                 with st.spinner("Simulando perfiles de presión..."):
                     try:
                         pwh_list = [float(p.strip()) for p in pwh_arr_input.split(',')]
                         import plotly.graph_objects as go
                         import copy
                         
                         fig = go.Figure()
                         fig.add_trace(go.Scatter(x=data["ipr"]["q"], y=data["ipr"]["pwf"], mode='lines', name='Curva IPR Base', line={"color": '#4f1dd7', "width": 4}))
                         
                         w_params = st.session_state["well_params"]
                         v_params = st.session_state["vlp_params"]
                         current_ipr_key = st.session_state.get("ipr_key", "darcy_radial")
                         
                         colors = ['#ef4444', '#f59e0b', '#10b981', '#3b82f6', '#8b5cf6']
                         
                         for idx, sim_pwh in enumerate(pwh_list):
                             sim_vlp = copy.deepcopy(v_params)
                             sim_vlp["p_wh"] = sim_pwh
                             
                             sim_data = generate_nodal_curves(w_params, sim_vlp, model_type=current_ipr_key)
                             
                             c = colors[idx % len(colors)]
                             fig.add_trace(go.Scatter(x=sim_data["vlp"]["q"], y=sim_data["vlp"]["pwf"], mode='lines', name=f'VLP (Pwh={sim_pwh})', line={"color": c, "width": 2}))
                             
                             if sim_data.get("intersection") and sim_data["intersection"]["q"]:
                                 fig.add_trace(go.Scatter(
                                     x=[sim_data["intersection"]["q"]], 
                                     y=[sim_data["intersection"]["pwf"]],
                                     mode='markers',
                                     showlegend=False,
                                     marker={"size": 10, "color": c, "symbol": 'circle'}
                                 ))
                         
                         st.success("Sensibilidad calculada.")
                         fig.update_layout(title="Sensibilidad de Presión en Cabezal vs IPR", xaxis_title="Caudal (STB/D)", yaxis_title="Presión de Fondo (psia)", height=600)
                         st.plotly_chart(fig, use_container_width=True)
                     except Exception as e:
                         st.error(f"Error procesando lista de presiones: {e}")

    else:
        st.warning("⚠️ No hay modelo activo. Por favor configure y ejecute el Análisis de Pozo primero.")

elif page == "Reporte Técnico":
    st.markdown('<div style="max-w-[850px] mx-auto bg-white dark:bg-slate-900 shadow-2xl rounded-2xl p-12 border border-slate-200 dark:border-slate-800">', unsafe_allow_html=True)
    
    st.markdown('<div style="text-align: center; margin-bottom: 3rem;">', unsafe_allow_html=True)
    st.markdown('<span class="material-symbols-outlined" style="font-size: 3rem; color: #4f1dd7;">article</span>', unsafe_allow_html=True)
    st.markdown('<h1 style="font-size: 2.5rem; font-weight: 800; color: #4f1dd7;">Reporte Técnico: Optimización Nodal</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color: #64748b;">Generado automáticamente por Nodal Analysis Pro Engine</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    if st.session_state.get("plot_data") and st.session_state["plot_data"].get("intersection"):
        data = st.session_state["plot_data"]
        op = data["intersection"]
        aof = max(data["ipr"]["q"])
        
        st.markdown('<h3>1. Resumen Ejecutivo</h3>', unsafe_allow_html=True)
        st.markdown(f'<p style="color: #475569; font-size: 1.1rem; line-height: 1.6;">El presente análisis determinístico indica que el pozo se encuentra en condición fluyente. El punto de operación proyectado se establece en una presión dinámica de fondo (Pwf) de <b>{op["pwf"]:,.1f} psia</b>, permitiendo un caudal de líquido de <b>{op["q"]:,.1f} STB/d</b>. El potencial máximo de yacimiento (AOF) se estima en <b>{aof:,.1f} STB/d</b>, lo que indica una eficiencia de extracción técnica del {(op["q"]/aof)*100:.1f}% respecto al teórico ideal sin contrapresión de tubería.</p>', unsafe_allow_html=True)
        
        st.divider()
        st.markdown('<h3>2. Parámetros de Operación</h3>', unsafe_allow_html=True)
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            st.markdown(f"**Tasa de Flujo Operativa:** {op['q']:,.1f} STB/d")
            st.markdown(f"**Pwf Operativa:** {op['pwf']:,.1f} psia")
        with col_r2:
            st.markdown(f"**Diámetro Interno (Tubing):** {st.session_state['well_state']['d_inner']} in")
            st.markdown(f"**Profundidad (MD):** {st.session_state['well_state']['md_total']} ft")
            
        st.divider()
        st.markdown('<h3>3. Validaciones Físicas</h3>', unsafe_allow_html=True)
        if op['pwf'] > 0:
            st.success("✅ Estabilidad de Flujo: Confirmada. El gradiente de presión supera las pérdidas por fricción e hidrostática.")
        else:
            st.error("🔴 Estabilidad de Flujo: Riesgo. Análisis indica posible cese de flujo.")
            
        st.markdown('<div style="text-align: center; margin-top: 4rem; color: #94a3b8; font-size: 0.8rem;">--- Fin del Reporte ---</div>', unsafe_allow_html=True)
    else:
        st.warning("⚠️ Ejecute primero un Análisis Nodal para recabar los datos operativos del pozo.")
        
    st.markdown('</div>', unsafe_allow_html=True)

else:
    # Render HTML using custom component wrapper for simple static pages (like Dashboard)
    target_html = html_map.get(page)
    if target_html and os.path.exists(target_html):
        render_stitch_html(target_html, height=1200)
    else:
        st.error(f"File not found: {target_html}")
