"""
Generate random patterns for council logos when no image is set.
Similar to Gravatar's identicons.
"""

import hashlib
import random
from typing import Tuple, List


def generate_pattern_svg(identifier: str, size: int = 200) -> str:
    """
    Generate an SVG pattern based on a unique identifier.
    
    Args:
        identifier: A unique string (e.g., council slug)
        size: The size of the SVG in pixels
        
    Returns:
        SVG markup as a string
    """
    # Create a deterministic random seed from the identifier
    hash_obj = hashlib.md5(identifier.encode('utf-8'))
    seed = int(hash_obj.hexdigest()[:8], 16)
    random.seed(seed)
    
    # Generate colour palette
    colours = _generate_colour_palette()
    bg_colour = colours[0]
    pattern_colours = colours[1:]
    
    # Create geometric pattern
    pattern_elements = _generate_geometric_pattern(size, pattern_colours)
    
    # Build SVG
    svg = f'''<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg">
    <rect width="{size}" height="{size}" fill="{bg_colour}"/>
    {pattern_elements}
</svg>'''
    
    return svg


def _generate_colour_palette() -> List[str]:
    """Generate a harmonious colour palette."""
    # Professional council-appropriate colours
    base_colours = [
        ['#2563eb', '#3b82f6', '#60a5fa'],  # Blues
        ['#059669', '#10b981', '#34d399'],  # Greens  
        ['#dc2626', '#ef4444', '#f87171'],  # Reds
        ['#7c3aed', '#8b5cf6', '#a78bfa'],  # Purples
        ['#ea580c', '#f97316', '#fb923c'],  # Oranges
        ['#0891b2', '#06b6d4', '#22d3ee'],  # Cyans
    ]
    
    # Pick a random colour family
    palette = random.choice(base_colours)
    
    # Add neutral background
    neutrals = ['#f8fafc', '#f1f5f9', '#e2e8f0']
    bg = random.choice(neutrals)
    
    return [bg] + palette


def _generate_geometric_pattern(size: int, colours: List[str]) -> str:
    """Generate geometric pattern elements."""
    elements = []
    
    # Choose pattern type
    pattern_type = random.choice(['circles', 'triangles', 'hexagons', 'diamonds'])
    
    if pattern_type == 'circles':
        elements = _generate_circle_pattern(size, colours)
    elif pattern_type == 'triangles':
        elements = _generate_triangle_pattern(size, colours)
    elif pattern_type == 'hexagons':
        elements = _generate_hexagon_pattern(size, colours)
    else:  # diamonds
        elements = _generate_diamond_pattern(size, colours)
    
    return '\n    '.join(elements)


def _generate_circle_pattern(size: int, colours: List[str]) -> List[str]:
    """Generate a pattern of circles."""
    elements = []
    
    # Grid of circles
    grid_size = random.choice([3, 4, 5])
    cell_size = size // grid_size
    
    for row in range(grid_size):
        for col in range(grid_size):
            # Skip some circles randomly for variation
            if random.random() < 0.3:
                continue
                
            cx = col * cell_size + cell_size // 2
            cy = row * cell_size + cell_size // 2
            radius = random.randint(cell_size // 4, cell_size // 3)
            colour = random.choice(colours)
            opacity = random.uniform(0.6, 0.9)
            
            elements.append(f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="{colour}" opacity="{opacity:.2f}"/>')
    
    return elements


def _generate_triangle_pattern(size: int, colours: List[str]) -> List[str]:
    """Generate a pattern of triangles."""
    elements = []
    
    # Grid of triangles
    grid_size = random.choice([4, 5, 6])
    cell_size = size // grid_size
    
    for row in range(grid_size):
        for col in range(grid_size):
            if random.random() < 0.4:
                continue
                
            x = col * cell_size
            y = row * cell_size
            
            # Random triangle orientation
            if random.choice([True, False]):
                # Upward triangle
                points = f"{x + cell_size//2},{y + 10} {x + 10},{y + cell_size - 10} {x + cell_size - 10},{y + cell_size - 10}"
            else:
                # Downward triangle  
                points = f"{x + 10},{y + 10} {x + cell_size - 10},{y + 10} {x + cell_size//2},{y + cell_size - 10}"
            
            colour = random.choice(colours)
            opacity = random.uniform(0.6, 0.9)
            
            elements.append(f'<polygon points="{points}" fill="{colour}" opacity="{opacity:.2f}"/>')
    
    return elements


def _generate_hexagon_pattern(size: int, colours: List[str]) -> List[str]:
    """Generate a pattern of hexagons."""
    elements = []
    
    # Honeycomb pattern
    hex_size = size // 6
    
    for row in range(5):
        for col in range(4):
            if random.random() < 0.3:
                continue
            
            # Offset every other row for honeycomb effect
            x_offset = (hex_size // 2) if row % 2 else 0
            x = col * hex_size * 1.5 + x_offset + hex_size
            y = row * hex_size * 0.866 + hex_size
            
            # Generate hexagon points
            points = []
            for i in range(6):
                angle = i * 60 * 3.14159 / 180
                px = x + hex_size * 0.5 * random.uniform(0.7, 1.0) * (1 if random.random() > 0.5 else -1) * abs(random.normalvariate(0, 0.2))
                py = y + hex_size * 0.5 * random.uniform(0.7, 1.0) * (1 if random.random() > 0.5 else -1) * abs(random.normalvariate(0, 0.2))
                points.append(f"{px:.1f},{py:.1f}")
            
            colour = random.choice(colours)
            opacity = random.uniform(0.6, 0.9)
            
            elements.append(f'<polygon points="{" ".join(points)}" fill="{colour}" opacity="{opacity:.2f}"/>')
    
    return elements


def _generate_diamond_pattern(size: int, colours: List[str]) -> List[str]:
    """Generate a pattern of diamonds."""
    elements = []
    
    # Grid of diamonds
    grid_size = random.choice([4, 5])
    cell_size = size // grid_size
    
    for row in range(grid_size):
        for col in range(grid_size):
            if random.random() < 0.35:
                continue
                
            cx = col * cell_size + cell_size // 2
            cy = row * cell_size + cell_size // 2
            diamond_size = random.randint(cell_size // 4, cell_size // 3)
            
            # Diamond is a rotated square
            points = f"{cx},{cy - diamond_size} {cx + diamond_size},{cy} {cx},{cy + diamond_size} {cx - diamond_size},{cy}"
            
            colour = random.choice(colours)
            opacity = random.uniform(0.6, 0.9)
            
            elements.append(f'<polygon points="{points}" fill="{colour}" opacity="{opacity:.2f}"/>')
    
    return elements


def get_pattern_data_url(identifier: str, size: int = 200) -> str:
    """
    Generate a data URL for the pattern SVG.
    
    Args:
        identifier: A unique string (e.g., council slug)
        size: The size of the SVG in pixels
        
    Returns:
        Data URL string that can be used directly in img src
    """
    svg = generate_pattern_svg(identifier, size)
    
    # Encode as data URL
    import base64
    svg_bytes = svg.encode('utf-8')
    svg_b64 = base64.b64encode(svg_bytes).decode('utf-8')
    
    return f"data:image/svg+xml;base64,{svg_b64}"


def get_pattern_css_background(identifier: str, size: int = 200) -> str:
    """
    Generate CSS background-image property for the pattern.
    
    Args:
        identifier: A unique string (e.g., council slug)
        size: The size of the SVG in pixels
        
    Returns:
        CSS background-image property value
    """
    data_url = get_pattern_data_url(identifier, size)
    return f"background-image: url('{data_url}');"