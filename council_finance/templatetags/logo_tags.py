"""
Template tags for handling council logos and image fields.
"""

from django import template
from django.utils.safestring import mark_safe
from django.utils.html import escape
from council_finance.models import DataField, ImageFile, CouncilCharacteristic
from council_finance.utils.pattern_generator import get_pattern_data_url

register = template.Library()


@register.simple_tag
def council_logo_img(council, size=64, css_classes=""):
    """
    Generate an img tag for the council logo.
    Falls back to a generated pattern if no logo is set.
    
    Args:
        council: Council object
        size: Size in pixels (default 64)
        css_classes: Additional CSS classes
    
    Returns:
        HTML img tag
    """
    # Try to get the logo field
    try:
        logo_field = DataField.objects.get(slug='council_logo', content_type='image')
    except DataField.DoesNotExist:
        # No logo field exists, use pattern
        return _generate_pattern_img(council, size, css_classes)
    
    # Try to get the council's logo
    try:
        characteristic = CouncilCharacteristic.objects.get(council=council, field=logo_field)
        if characteristic.value:
            # Value should be the ID of an ImageFile
            try:
                image_file = ImageFile.objects.get(id=characteristic.value, is_active=True, is_approved=True)
                return _generate_logo_img(image_file, council, size, css_classes)
            except (ImageFile.DoesNotExist, ValueError):
                pass
    except CouncilCharacteristic.DoesNotExist:
        pass
    
    # Fall back to pattern
    return _generate_pattern_img(council, size, css_classes)


@register.simple_tag  
def council_logo_url(council, size=64):
    """
    Get the URL for the council logo.
    Returns a data URL for a generated pattern if no logo is set.
    
    Args:
        council: Council object
        size: Size in pixels (default 64)
    
    Returns:
        URL string
    """
    # Try to get the logo field
    try:
        logo_field = DataField.objects.get(slug='council_logo', content_type='image')
    except DataField.DoesNotExist:
        # No logo field exists, use pattern
        return get_pattern_data_url(council.slug, size)
    
    # Try to get the council's logo
    try:
        characteristic = CouncilCharacteristic.objects.get(council=council, field=logo_field)
        if characteristic.value:
            try:
                image_file = ImageFile.objects.get(id=characteristic.value, is_active=True, is_approved=True)
                return image_file.file.url
            except (ImageFile.DoesNotExist, ValueError):
                pass
    except CouncilCharacteristic.DoesNotExist:
        pass
    
    # Fall back to pattern
    return get_pattern_data_url(council.slug, size)


def _generate_logo_img(image_file, council, size, css_classes):
    """Generate img tag for an actual logo file."""
    alt_text = image_file.alt_text or image_file.field.image_default_alt_text or f"{council.name} logo"
    
    # Build img tag
    img_attrs = [
        f'src="{escape(image_file.file.url)}"',
        f'alt="{escape(alt_text)}"',
        f'width="{size}"',
        f'height="{size}"',
    ]
    
    if css_classes:
        img_attrs.append(f'class="{escape(css_classes)}"')
    
    return mark_safe(f'<img {" ".join(img_attrs)}>')


def _generate_pattern_img(council, size, css_classes):
    """Generate img tag for a pattern fallback."""
    data_url = get_pattern_data_url(council.slug, size)
    alt_text = f"{council.name} pattern"
    
    # Build img tag
    img_attrs = [
        f'src="{data_url}"',
        f'alt="{escape(alt_text)}"',
        f'width="{size}"',
        f'height="{size}"',
    ]
    
    if css_classes:
        img_attrs.append(f'class="{escape(css_classes)}"')
    
    return mark_safe(f'<img {" ".join(img_attrs)}>')


@register.simple_tag
def council_logo_div(council, size=64, css_classes=""):
    """
    Generate a div with background image for the council logo.
    Falls back to a generated pattern if no logo is set.
    
    Args:
        council: Council object
        size: Size in pixels (default 64)
        css_classes: Additional CSS classes
    
    Returns:
        HTML div tag with background image
    """
    logo_url = council_logo_url(council, size)
    
    # Build style attribute
    style_parts = [
        f'width: {size}px',
        f'height: {size}px', 
        f'background-image: url({logo_url})',
        'background-size: cover',
        'background-position: center',
        'background-repeat: no-repeat'
    ]
    
    div_attrs = [f'style="{"; ".join(style_parts)}"']
    
    if css_classes:
        div_attrs.append(f'class="{escape(css_classes)}"')
    
    return mark_safe(f'<div {" ".join(div_attrs)}></div>')


@register.filter
def has_logo(council):
    """
    Check if a council has a logo set.
    
    Args:
        council: Council object
    
    Returns:
        Boolean
    """
    try:
        logo_field = DataField.objects.get(slug='council_logo', content_type='image')
        characteristic = CouncilCharacteristic.objects.get(council=council, field=logo_field)
        if characteristic.value:
            return ImageFile.objects.filter(id=characteristic.value, is_active=True, is_approved=True).exists()
    except (DataField.DoesNotExist, CouncilCharacteristic.DoesNotExist, ValueError):
        pass
    
    return False