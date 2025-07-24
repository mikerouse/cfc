from django import template
from django.conf import settings
from django.utils.safestring import mark_safe
import json
import os

register = template.Library()

@register.simple_tag
def vite_asset(path: str):
    if settings.DEBUG:
        return mark_safe(f'<script type="module" src="http://localhost:5173/@vite/client"></script><script type="module" src="http://localhost:5173/{path}"></script>')
    else:
        manifest_path = os.path.join(settings.BASE_DIR, 'static', 'frontend', '.vite', 'manifest.json')
        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
        except FileNotFoundError:
            raise Exception(f"Vite manifest not found at {manifest_path}")

        asset_info = manifest.get(path)
        if not asset_info:
            raise Exception(f"Asset not found in Vite manifest: {path}")

        html = f'<script type="module" src="/static/frontend/{asset_info["file"]}"></script>'
        if 'css' in asset_info:
            for css_file in asset_info['css']:
                html += f'<link rel="stylesheet" href="/static/frontend/{css_file}">'
        
        return mark_safe(html)
