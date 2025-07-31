from django import template
from django.conf import settings
from django.templatetags.static import static
import json
import os

register = template.Library()

_manifest_cache = None

def _load_manifest():
    global _manifest_cache
    # In development, always reload the manifest to pick up new builds
    if settings.DEBUG or _manifest_cache is None:
        manifest_path = os.path.join(settings.BASE_DIR, 'static', 'frontend', '.vite', 'manifest.json')
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                _manifest_cache = json.load(f)
        except FileNotFoundError:
            _manifest_cache = {}
    return _manifest_cache

@register.simple_tag
def vite_js(entry='src/main.jsx'):
    # In development, use stable filenames
    if settings.DEBUG:
        return static('frontend/main.js')
    
    # In production, use manifest
    manifest = _load_manifest()
    info = manifest.get(entry, {})
    file = info.get('file')
    if file:
        return static(f'frontend/{file}')
    return static('frontend/main.js')  # Fallback

@register.simple_tag
def vite_css(entry='src/main.jsx'):
    # In development, use stable filenames
    if settings.DEBUG:
        return static('frontend/main.css')
    
    # In production, use manifest
    manifest = _load_manifest()
    info = manifest.get(entry, {})
    css_files = info.get('css', [])
    if css_files:
        return static(f'frontend/{css_files[0]}')
    return static('frontend/main.css')  # Fallback
