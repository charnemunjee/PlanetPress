# -- PlanetPress Sphinx configuration ---------------------------------------

import os
import sys
import django

# Add project root to Python path
sys.path.insert(0, os.path.abspath(".."))

# Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "PlanetPress.settings")
django.setup()

# -- Project information -----------------------------------------------------

project = "planetpress"
author = "Charne"
release = "0.1.0"

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

templates_path = ["_templates"]
exclude_patterns = []

# Autodoc settings
autodoc_member_order = "bysource"
autodoc_inherit_docstrings = True
napoleon_google_docstring = True
napoleon_numpy_docstring = True

# -- Options for HTML output -------------------------------------------------

html_theme = "alabaster"  # You can change to "furo" if installed
html_static_path = ["_static"]

# -- Options for autodoc -----------------------------------------------------

# Show type hints in the description instead of signature
autodoc_typehints = "description"
