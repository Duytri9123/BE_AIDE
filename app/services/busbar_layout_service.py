"""
Busbar Sizing & CAD Layout Calculation Engine
Calculates copper busbar cross-sections, terminal hole coordinates, and 2D/3D layouts.
"""
from typing import Dict, List, Any, Optional, Tuple
import math

# Copper Bar Specifications: (Width mm, Thickness mm, Max Continuous Current A at 35C in enclosure, Weight kg/m)
STANDARD_COPPER_BARS = [
    {"width": 15, "thickness": 3, "area": 45, "max_amps": 140, "weight_kg_m": 0.40, "label": "15x3 mm"},
    {"width": 20, "thickness": 3, "area": 60, "max_amps": 185, "weight_kg_m": 0.53, "label": "20x3 mm"},
    {"width": 25, "thickness": 3, "area": 75, "max_amps": 230, "weight_kg_m": 0.67, "label": "25x3 mm"},
    {"width": 25, "thickness": 4, "area": 100, "max_amps": 290, "weight_kg_m": 0.89, "label": "25x4 mm"},
    {"width": 30, "thickness": 4, "area": 120, "max_amps": 340, "weight_kg_m": 1.07, "label": "30x4 mm"},
    {"width": 30, "thickness": 5, "area": 150, "max_amps": 400, "weight_kg_m": 1.34, "label": "30x5 mm"},
    {"width": 40, "thickness": 5, "area": 200, "max_amps": 500, "weight_kg_m": 1.78, "label": "40x5 mm"},
    {"width": 50, "thickness": 5, "area": 250, "max_amps": 600, "weight_kg_m": 2.23, "label": "50x5 mm"},
    {"width": 50, "thickness": 6, "area": 300, "max_amps": 680, "weight_kg_m": 2.67, "label": "50x6 mm"},
    {"width": 60, "thickness": 6, "area": 360, "max_amps": 780, "weight_kg_m": 3.20, "label": "60x6 mm"},
    {"width": 60, "thickness": 8, "area": 480, "max_amps": 920, "weight_kg_m": 4.27, "label": "60x8 mm"},
    {"width": 80, "thickness": 8, "area": 640, "max_amps": 1120, "weight_kg_m": 5.70, "label": "80x8 mm"},
    {"width": 80, "thickness": 10, "area": 800, "max_amps": 1300, "weight_kg_m": 7.12, "label": "80x10 mm"},
    {"width": 100, "thickness": 10, "area": 1000, "max_amps": 1550, "weight_kg_m": 8.90, "label": "100x10 mm"},
    {"width": 80, "thickness": 10, "bars_qty": 2, "area": 1600, "max_amps": 2100, "weight_kg_m": 14.24, "label": "2x(80x10) mm"},
    {"width": 100, "thickness": 10, "bars_qty": 2, "area": 2000, "max_amps": 2500, "weight_kg_m": 17.80, "label": "2x(100x10) mm"},
    {"width": 100, "thickness": 10, "bars_qty": 3, "area": 3000, "max_amps": 3300, "weight_kg_m": 26.70, "label": "3x(100x10) mm"},
]

def calculate_busbar_sizing(
    in_current: float,
    ambient_temp: float = 35.0,
    ip_rating: str = "IP41",
    safety_margin: float = 1.15
) -> Dict[str, Any]:
    """
    Selects the optimal copper busbar dimension for a given rated current In.
    Applies temperature derating and enclosure IP factors.
    """
    # Temperature correction factor (Base: 35 deg C)
    if ambient_temp <= 30:
        k_temp = 1.05
    elif ambient_temp <= 35:
        k_temp = 1.0
    elif ambient_temp <= 40:
        k_temp = 0.94
    elif ambient_temp <= 45:
        k_temp = 0.88
    else:
        k_temp = 0.82

    # Enclosure IP rating factor
    if ip_rating in ["IP00", "IP20", "IP30"]:
        k_ip = 1.0
    elif ip_rating in ["IP40", "IP41", "IP42"]:
        k_ip = 0.92
    else: # IP54, IP55, IP65
        k_ip = 0.85

    design_current = in_current * safety_margin
    effective_current_capacity = design_current / (k_temp * k_ip)

    recommended_bar = None
    alternatives = []

    for bar in STANDARD_COPPER_BARS:
        if bar["max_amps"] >= effective_current_capacity:
            if recommended_bar is None:
                recommended_bar = bar
            else:
                alternatives.append(bar)

    if recommended_bar is None:
        recommended_bar = STANDARD_COPPER_BARS[-1]

    # Calculate voltage drop per 1 meter for 3-phase (mV/A/m for copper ~ 0.018 ohm*mm2/m)
    rho_copper = 0.0178  # ohm * mm2 / m at 20C, approx 0.021 at 70C
    r_per_meter = (0.021 / recommended_bar["area"])  # ohm/m
    v_drop_per_meter = math.sqrt(3) * in_current * r_per_meter

    return {
        "rated_current_a": in_current,
        "design_current_a": round(design_current, 2),
        "required_capacity_a": round(effective_current_capacity, 2),
        "ambient_temp_c": ambient_temp,
        "ip_rating": ip_rating,
        "derating_factor": round(k_temp * k_ip, 3),
        "recommended_busbar": recommended_bar,
        "alternatives": alternatives[:3],
        "resistance_ohm_per_meter": round(r_per_meter, 6),
        "voltage_drop_v_per_meter": round(v_drop_per_meter, 4),
        "power_loss_w_per_meter": round(3 * (in_current ** 2) * r_per_meter, 2)
    }

def generate_busbar_hole_layout(
    device_width: float,
    device_height: float,
    device_depth: float,
    poles: int,
    pitch: Optional[float] = None,
    pole_w: Optional[float] = None,
    busbar_level: Optional[float] = None,
    busbar_holes_spec: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Computes precise 2D and 3D coordinates for busbar connection holes for each phase.
    """
    p = max(1, poles)
    w = device_width
    h = device_height
    d = device_depth

    # Determine pitch if not provided
    eff_pitch = pitch if (pitch and pitch > 0) else (w / p)
    eff_pole_w = pole_w if (pole_w and pole_w > 0) else (w / (p * 2))
    eff_b_level = busbar_level if (busbar_level and busbar_level > 0) else (d * 0.35)

    spec = busbar_holes_spec or {}
    depth = spec.get("depth", 15)
    dia = spec.get("dia") or (6 if h < 150 else (10 if h < 270 else 14))
    rows = spec.get("rows", [])

    phase_names = ["R (L1)", "S (L2)", "T (L3)", "N"] if p == 4 else (["R (L1)", "S (L2)", "T (L3)"] if p == 3 else ([f"P{i+1}" for i in range(p)]))

    # Calculate center X for each pole
    # If pitch-based, center the array of poles on the device width
    total_poles_span = (p - 1) * eff_pitch
    start_x = (w - total_poles_span) / 2.0

    terminals = []
    for i in range(p):
        pole_center_x = round(start_x + i * eff_pitch, 2)
        phase_label = phase_names[i] if i < len(phase_names) else f"P{i+1}"

        # Top Terminal (Line / In)
        top_holes = []
        # Bottom Terminal (Load / Out)
        bottom_holes = []

        if rows:
            for r in rows:
                y_off = r.get("y", 10)
                x_offsets = r.get("x_off", [0])
                for xoff in x_offsets:
                    hole_x = round(pole_center_x + xoff, 2)
                    top_holes.append({"x": hole_x, "y": round(h - y_off, 2), "z": eff_b_level, "dia": dia})
                    bottom_holes.append({"x": hole_x, "y": round(y_off, 2), "z": eff_b_level, "dia": dia})
        else:
            # Standard single hole per terminal
            top_y = round(h - depth / 2.0, 2)
            bottom_y = round(depth / 2.0, 2)
            top_holes.append({"x": pole_center_x, "y": top_y, "z": eff_b_level, "dia": dia})
            bottom_holes.append({"x": pole_center_x, "y": bottom_y, "z": eff_b_level, "dia": dia})

        terminals.append({
            "pole_index": i,
            "phase": phase_label,
            "center_x": pole_center_x,
            "top_terminal": {
                "bounds": {
                    "x_min": round(pole_center_x - eff_pole_w / 2.0, 2),
                    "x_max": round(pole_center_x + eff_pole_w / 2.0, 2),
                    "y_min": round(h - depth, 2),
                    "y_max": h
                },
                "holes": top_holes
            },
            "bottom_terminal": {
                "bounds": {
                    "x_min": round(pole_center_x - eff_pole_w / 2.0, 2),
                    "x_max": round(pole_center_x + eff_pole_w / 2.0, 2),
                    "y_min": 0,
                    "y_max": depth
                },
                "holes": bottom_holes
            }
        })

    return {
        "device_dimensions": {"width": w, "height": h, "depth": d},
        "poles_count": p,
        "pitch": eff_pitch,
        "pole_width": eff_pole_w,
        "busbar_z_elevation": eff_b_level,
        "hole_diameter": dia,
        "terminals": terminals
    }

def generate_mounting_template(
    device_width: float,
    device_height: float,
    mount_holes_spec: Optional[Dict[str, Any]] = None,
    clearance: float = 8.0,
    creepage: float = 10.0
) -> Dict[str, Any]:
    """
    Computes mounting hole layout and enclosure clearance envelope.
    """
    w = device_width
    h = device_height

    spec = mount_holes_spec or {}
    points = spec.get("points", [])
    dia = spec.get("dia", 4)

    if not points:
        # Default 4 corner holes if none specified
        points = [
            [round(w * 0.15, 2), round(h * 0.1, 2)],
            [round(w * 0.85, 2), round(h * 0.1, 2)],
            [round(w * 0.15, 2), round(h * 0.9, 2)],
            [round(w * 0.85, 2), round(h * 0.9, 2)]
        ]

    # Clearance envelope
    envelope = {
        "width": round(w + clearance * 2, 2),
        "height": round(h + clearance * 2, 2),
        "clearance_side": clearance,
        "creepage_distance": creepage
    }

    return {
        "device_size": {"width": w, "height": h},
        "hole_diameter": dia,
        "mounting_points": [{"x": pt[0], "y": pt[1]} for pt in points],
        "clearance_envelope": envelope
    }

def generate_device_cad_svg(device_data: Dict[str, Any]) -> str:
    """
    Generates a 2D SVG vector graphic representation of the device with terminals and busbar holes.
    """
    dims = device_data.get("dimensions", {})
    w = float(dims.get("w", 75))
    h = float(dims.get("h", 130))
    d = float(dims.get("d", 82))
    params = device_data.get("parameters", {})
    poles = int(params.get("p", 3))
    sku = device_data.get("sku", "DEVICE")
    name = device_data.get("name", sku)
    in_a = params.get("in", 0)
    icu_ka = params.get("icu", 0)

    layout = generate_busbar_hole_layout(
        device_width=w,
        device_height=h,
        device_depth=d,
        poles=poles,
        pitch=dims.get("pitch"),
        pole_w=dims.get("pole_w"),
        busbar_level=dims.get("busbar_level"),
        busbar_holes_spec=params.get("busbar_holes")
    )

    pad = 20
    svg_w = w + pad * 2
    svg_h = h + pad * 2

    # Build SVG XML
    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}" width="{svg_w*2}" height="{svg_h*2}">',
        f'  <defs>',
        f'    <pattern id="grid" width="10" height="10" patternUnits="userSpaceOnUse">',
        f'      <path d="M 10 0 L 0 0 0 10" fill="none" stroke="#1e293b" stroke-width="0.5"/>',
        f'    </pattern>',
        f'  </defs>',
        f'  <!-- Background -->',
        f'  <rect width="{svg_w}" height="{svg_h}" fill="#0f172a"/>',
        f'  <rect width="{svg_w}" height="{svg_h}" fill="url(#grid)"/>',
        f'  <g transform="translate({pad}, {pad})">',
        f'    <!-- Device Body -->',
        f'    <rect x="0" y="0" width="{w}" height="{h}" rx="3" fill="#1e293b" stroke="#38bdf8" stroke-width="1.5"/>',
        f'    <!-- Device Center Label -->',
        f'    <text x="{w/2}" y="{h/2 - 6}" fill="#f8fafc" font-size="6" font-weight="bold" text-anchor="middle" font-family="monospace">{sku}</text>',
        f'    <text x="{w/2}" y="{h/2 + 4}" fill="#94a3b8" font-size="5" text-anchor="middle" font-family="sans-serif">{in_a}A / {icu_ka}kA</text>',
    ]

    # Draw terminals & holes
    for term in layout["terminals"]:
        phase = term["phase"]
        # Top terminal
        top_b = term["top_terminal"]["bounds"]
        top_w = top_b["x_max"] - top_b["x_min"]
        top_h = top_b["y_max"] - top_b["y_min"]
        svg_parts.append(f'    <!-- Top Terminal {phase} -->')
        svg_parts.append(f'    <rect x="{top_b["x_min"]}" y="{h - top_b["y_max"]}" width="{top_w}" height="{top_h}" fill="#334155" stroke="#f59e0b" stroke-width="0.8"/>')
        for h_info in term["top_terminal"]["holes"]:
            svg_parts.append(f'    <circle cx="{h_info["x"]}" cy="{h - h_info["y"]}" r="{h_info["dia"]/2}" fill="#0f172a" stroke="#fbbf24" stroke-width="0.8"/>')

        # Bottom terminal
        bot_b = term["bottom_terminal"]["bounds"]
        bot_w = bot_b["x_max"] - bot_b["x_min"]
        bot_h = bot_b["y_max"] - bot_b["y_min"]
        svg_parts.append(f'    <!-- Bottom Terminal {phase} -->')
        svg_parts.append(f'    <rect x="{bot_b["x_min"]}" y="{h - bot_b["y_max"]}" width="{bot_w}" height="{bot_h}" fill="#334155" stroke="#10b981" stroke-width="0.8"/>')
        for h_info in term["bottom_terminal"]["holes"]:
            svg_parts.append(f'    <circle cx="{h_info["x"]}" cy="{h - h_info["y"]}" r="{h_info["dia"]/2}" fill="#0f172a" stroke="#34d399" stroke-width="0.8"/>')

        # Phase label
        svg_parts.append(f'    <text x="{term["center_x"]}" y="{h + 10}" fill="#cbd5e1" font-size="4.5" text-anchor="middle" font-family="sans-serif">{phase}</text>')

    svg_parts.append('  </g>')
    svg_parts.append('</svg>')

    return "\n".join(svg_parts)
