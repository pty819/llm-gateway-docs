project = 'LLM Gateway'
copyright = '2026, Yifan Li'
author = 'Yifan Li'
release = '1.0.0'

extensions = [
    'sphinxcontrib.mermaid',
    'myst_parser',
    'sphinx_copybutton',
    'sphinx_tabs.tabs',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

myst_enable_extensions = [
    'colon_fence',
    'deflist',
    'directive',
]

mermaid_version = '11.4.0'

html_theme_options = {
    'prev_next_buttons_location': 'bottom',
    'style_external_links': False,
    'style_nav_header_background': '#2980b9',
}

master_doc = 'index'
