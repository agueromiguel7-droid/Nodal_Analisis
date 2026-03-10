import streamlit.components.v1 as components
import json
import os

# Declare the bidirectional custom component that points to the new HTML folder
_well_analysis_component = components.declare_component(
    "well_analysis_component",
    path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "stitch_preview", "well_analysis_component")
)

def well_analysis_component(plot_data=None, key=None):
    return _well_analysis_component(plot_data=plot_data, key=key, default=None)

def render_stitch_html(filepath, height=1200, plot_data=None):
    """
    Renders a dummy one-way HTML file within Streamlit using an iframe wrapper.
    Used for pages that don't need to send data back yet.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        html_content = f.read()
        
    # Inject CSS to hide the static HTML sidebar and adjust the main content to take full width
    css_injection = """
    <style>
        aside { display: none !important; }
        header { width: 100% !important; }
        .flex-1 { width: 100% !important; }
    </style>
    """
    html_content = html_content + css_injection
    
    if plot_data:
        json_data = json.dumps(plot_data)
        js_injection = f"""
        <script>
            setTimeout(function() {{
                window.postMessage({{
                    type: "streamlit:render",
                    args: {json_data}
                }}, "*");
            }}, 500);
        </script>
        """
        html_content = html_content + js_injection
    
    components.html(html_content, height=height, scrolling=True)
