"""Eight-view industrial cabinet renderer matching the approved fabrication UI."""
from typing import Any, Dict, List

from ezdxf.enums import TextEntityAlignment

from app.services.cad.physical_layout_engine import PhysicalLayoutEngine


def _box(msp, x, y, w, h, layer="0_FRAME", color=None, lw=25):
    attrs = {"layer": layer, "lineweight": lw}
    if color is not None:
        attrs["color"] = color
    return msp.add_lwpolyline(
        [(x, y), (x + w, y), (x + w, y + h), (x, y + h)], close=True, dxfattribs=attrs
    )


def _line(msp, a, b, layer="0_DEVICES", color=None, lw=18):
    attrs = {"layer": layer, "lineweight": lw}
    if color is not None:
        attrs["color"] = color
    return msp.add_line(a, b, dxfattribs=attrs)


def _txt(msp, value, x, y, h=18, layer="0_TEXT", color=None,
         align=TextEntityAlignment.MIDDLE_CENTER, rotation=0):
    attrs = {"layer": layer, "height": h}
    if color is not None:
        attrs["color"] = color
    entity = msp.add_text(str(value), dxfattribs=attrs).set_placement((x, y), align=align)
    entity.dxf.rotation = rotation
    return entity


def _circle(msp, x, y, radius, layer="0_DEVICES", color=None, lw=22):
    attrs = {"layer": layer, "lineweight": lw}
    if color is not None:
        attrs["color"] = color
    return msp.add_circle((x, y), radius, dxfattribs=attrs)


def _dim_h(msp, x, y, width, label):
    yy = y - 60
    _line(msp, (x, yy), (x + width, yy), "0_DIM", 4, 13)
    _line(msp, (x, y), (x, yy - 10), "0_DIM", 4, 13)
    _line(msp, (x + width, y), (x + width, yy - 10), "0_DIM", 4, 13)
    _txt(msp, label, x + width / 2, yy + 17, 20, "0_DIM", 4)


def _dim_v(msp, x, y, height, label, offset=60):
    xx = x - offset
    _line(msp, (xx, y), (xx, y + height), "0_DIM", 4, 13)
    _line(msp, (x, y), (xx - 10, y), "0_DIM", 4, 13)
    _line(msp, (x, y + height), (xx - 10, y + height), "0_DIM", 4, 13)
    _txt(msp, label, xx - 16, y + height / 2, 20, "0_DIM", 4, rotation=90)


def _cabinet(msp, x, y, width, body_h, plinth):
    _box(msp, x, y + plinth, width, body_h, "0_FRAME", 7, 35)
    if plinth:
        _box(msp, x, y, width, plinth, "0_FRAME", 7, 35)


def _hinge(msp, x, y, side="right"):
    stem_x = x - 5 if side == "right" else x + 5
    _box(msp, stem_x - 5, y - 22, 10, 44, "0_HARDWARE", 7, 20)
    _circle(msp, stem_x, y - 13, 3, "0_HARDWARE", 7, 13)
    _circle(msp, stem_x, y + 13, 3, "0_HARDWARE", 7, 13)


def _perforated_bar(msp, x, y, w, h, color=6, vertical=True):
    _box(msp, x, y, w, h, "0_COPPER_SUPPORT", color, 22)
    count = max(3, int((h if vertical else w) / 32))
    for idx in range(count):
        if vertical:
            cx, cy = x + w / 2, y + (idx + .5) * h / count
        else:
            cx, cy = x + (idx + .5) * w / count, y + h / 2
        _circle(msp, cx, cy, 3, "0_PUNCH", 7, 13)


def _title(msp, value, x, y, width, total_h):
    _txt(msp, value, x + width / 2, y + total_h + 72, 28, "0_TEXT_TITLE", 1)


def _louver(msp, x, y, width, height):
    for col in range(3):
        for row in range(9):
            cw, rh = width / 3.0, height / 9.0
            _box(msp, x + col * cw + 4, y + row * rh + 4, cw - 8, rh - 8, "0_PLATE", 4, 13)


def _breaker(msp, x, y, w, h, tag, label, rotated=False, color=4):
    _box(msp, x, y, w, h, "0_DEVICES", color, 30)
    if rotated:
        for i in (1, 2):
            _line(msp, (x, y + i * h / 3), (x + w, y + i * h / 3), "0_DEVICES", color)
    else:
        for i in (1, 2):
            _line(msp, (x + i * w / 3, y), (x + i * w / 3, y + h), "0_DEVICES", color)
    _box(msp, x + w * .38, y + h * .37, w * .24, h * .26, "0_DEVICES", 2, 20)
    # Three poles, line/load terminals and mechanism window.  These details
    # remain visible in both elevation and side fabrication plots.
    if rotated:
        for pole in range(3):
            py = y + (pole + .5) * h / 3
            _circle(msp, x + 7, py, 2.8, "0_TERMINALS", 7, 15)
            _circle(msp, x + w - 7, py, 2.8, "0_TERMINALS", 7, 15)
            _line(msp, (x + 18, py), (x + w * .34, py), "0_DEVICES", 7, 13)
            _line(msp, (x + w * .66, py), (x + w - 18, py), "0_DEVICES", 7, 13)
    else:
        for pole in range(3):
            px = x + (pole + .5) * w / 3
            _circle(msp, px, y + 7, 2.8, "0_TERMINALS", 7, 15)
            _circle(msp, px, y + h - 7, 2.8, "0_TERMINALS", 7, 15)
            _line(msp, (px, y + 17), (px, y + h * .34), "0_DEVICES", 7, 13)
            _line(msp, (px, y + h * .66), (px, y + h - 17), "0_DEVICES", 7, 13)
    _txt(msp, tag, x + w / 2, y + h * .77, max(11, min(16, w / 6)), "0_TEXT", 7)
    _txt(msp, label, x + w / 2, y + h * .15, max(8, min(12, w / 9)), "0_TEXT", 7)
    for hx, hy in ((x + 7, y + 7), (x + w - 7, y + 7), (x + 7, y + h - 7), (x + w - 7, y + h - 7)):
        _circle(msp, hx, hy, 2.2, "0_PUNCH", 1, 13)


def _meter(msp, x, y, tag):
    _box(msp, x, y, 78, 78, "0_DOOR_ITEMS", 4, 25)
    _circle(msp, x + 39, y + 39, 25, "0_DOOR_ITEMS", 7, 16)
    _txt(msp, tag, x + 39, y + 39, 13, "0_TEXT", 7)


def _device_by_tag(devices: List[Dict[str, Any]], tag: str):
    target = str(tag or "").upper()
    return next((d for d in devices if str(d.get("tag") or "").upper() == target), None)


def draw_reference_eight_views(
    msp,
    devices: List[Dict[str, Any]],
    panel_code: str,
    panel_name: str,
    specs: Dict[str, Any],
    x_offset: float = 0.0,
    y_offset: float = 100.0,
    draw_busbar: bool = True,
):
    """Draw the approved eight-view UI for central-busbar distribution panels."""
    H = float(specs["height"])
    W = float(specs["width"])
    D = float(specs["depth"])
    P = float(specs.get("plinth_height") or 0)
    total_h = H + P
    gap = 150.0
    y = y_offset

    protection = [d for d in devices if str(d.get("category") or "").upper() in {"ACB", "MCCB", "MCB", "RCBO", "RCCB", "ELCB"}]
    explicit = [d for d in protection if str(d.get("section") or "").upper() in {"INCOMER", "ĐẦU VÀO", "DAU VAO", "NGUỒN CẤP", "NGUON CAP"}]
    incomer = max(explicit or protection or devices or [{}], key=lambda d: float(d.get("in_a") or 0))
    branches = [d for d in protection if d is not incomer]
    inc_w, inc_h, inc_d = PhysicalLayoutEngine.get_component_dimensions(incomer)

    columns = specs.get("central_columns") or {}
    by_tag = {str(d.get("tag") or "").upper(): d for d in branches}
    left = [by_tag.get(str(d.get("tag") or "").upper(), d) for d in (columns.get("left") or [])]
    right = [by_tag.get(str(d.get("tag") or "").upper(), d) for d in (columns.get("right") or [])]
    if not left and not right:
        split = (len(branches) + 1) // 2
        left, right = branches[:split], branches[split:]

    # 1. REAR
    x1 = x_offset + 90
    _title(msp, "MAT LUNG", x1, y, W, total_h)
    _cabinet(msp, x1, y, W, H, P)
    _box(msp, x1 + 50, y + P + 45, W - 100, H - 90, "0_PLATE", 7, 22)
    for px, py in ((70, P + 65), (W - 70, P + 65), (70, total_h - 65), (W - 70, total_h - 65)):
        _circle(msp, x1 + px, y + py, 4, "0_PUNCH", 4)
    _dim_h(msp, x1, y, W, f"{int(W)}")
    _dim_v(msp, x1, y + P, H, f"{int(H)}")
    if P:
        _dim_v(msp, x1, y, P, f"{int(P)}", 25)

    # 2. SIDE
    x2 = x1 + W + gap
    _title(msp, "MAT CANH", x2, y, D, total_h)
    _cabinet(msp, x2, y, D, H, P)
    _louver(msp, x2 + D * .20, y + P + H * .68, D * .60, H * .18)
    _louver(msp, x2 + D * .20, y + P + H * .15, D * .60, H * .18)
    for hy in (y + P + H * .20, y + P + H * .50, y + P + H * .80):
        _hinge(msp, x2 + D, hy)
    _dim_h(msp, x2, y, D, f"{int(D)}")

    # 3. FRONT DOOR
    x3 = x2 + D + gap
    _title(msp, "MAT TRUOC", x3, y, W, total_h)
    _cabinet(msp, x3, y, W, H, P)
    _box(msp, x3 + 25, y + P + 25, W - 50, H - 50, "0_FRAME", 7, 20)
    _box(msp, x3 + W * .34, y + P + H - 62, W * .32, 24, "0_DOOR_ITEMS", 4, 18)
    lamp_y = y + P + H - 115
    for i, (phase, col) in enumerate((("R", 1), ("S", 2), ("T", 5))):
        _circle(msp, x3 + W / 2 - 85 + i * 85, lamp_y, 16, "0_DOOR_ITEMS", col)
        _txt(msp, phase, x3 + W / 2 - 85 + i * 85, lamp_y - 32, 12)
    meter_y = lamp_y - 155
    for i, tag in enumerate(("A-R", "A-S", "A-T")):
        _meter(msp, x3 + W / 2 - 145 + i * 105, meter_y, tag)
    _meter(msp, x3 + W / 2 - 78, meter_y - 115, "V")
    _circle(msp, x3 + W / 2 + 75, meter_y - 76, 23, "0_DOOR_ITEMS", 4)
    _txt(msp, "VS", x3 + W / 2 + 75, meter_y - 76, 12)
    _box(msp, x3 + 65, y + P + H * .43, 30, 135, "0_DOOR_ITEMS", 7, 18)
    _box(msp, x3 + W / 2 - 48, y + P + 78, 96, 72, "0_DOOR_ITEMS", 2, 22)
    for hy in (y + P + H * .18, y + P + H * .50, y + P + H * .82):
        _hinge(msp, x3 + W, hy)

    # 4. INNER COVER
    x4 = x3 + W + gap
    _title(msp, "MAT CANH TRONG", x4, y, W, total_h)
    _cabinet(msp, x4, y, W, H, P)
    _box(msp, x4 + 35, y + P + 35, W - 70, H - 70, "0_PLATE", 7, 25)
    _line(msp, (x4 + 35, y + P + 35), (x4 + 58, y + P + 58), "0_PLATE", 7)
    _line(msp, (x4 + W - 35, y + P + 35), (x4 + W - 58, y + P + 58), "0_PLATE", 7)
    _line(msp, (x4 + 35, y + P + H - 35), (x4 + 58, y + P + H - 58), "0_PLATE", 7)
    _line(msp, (x4 + W - 35, y + P + H - 35), (x4 + W - 58, y + P + H - 58), "0_PLATE", 7)
    main_cx = x4 + W / 2
    main_cy = y + P + H * .72
    _box(msp, main_cx - 105, main_cy - 70, 210, 140, "0_PLATE", 4, 30)
    _box(msp, main_cx - 74, main_cy - 38, 148, 76, "0_DEVICES", 4, 20)
    for pole in range(3):
        _box(msp, main_cx - 66 + pole * 45, main_cy - 28, 34, 56, "0_DEVICES", 7, 15)
    tiers = max(len(left), len(right), 1)
    lower_y, upper_y = y + P + 245, y + P + H * .61
    step = (upper_y - lower_y) / max(1, tiers - 1)
    for i in range(tiers):
        cy = lower_y + i * step
        if i < len(left):
            _box(msp, x4 + 176, cy - 43, 56, 86, "0_DEVICES", 4, 20)
            _box(msp, x4 + 185, cy - 33, 38, 66, "0_DEVICES", 7, 13)
            _txt(msp, left[i].get("tag", ""), x4 + 265, cy, 11)
        if i < len(right):
            _box(msp, x4 + W - 232, cy - 43, 56, 86, "0_DEVICES", 4, 20)
            _box(msp, x4 + W - 223, cy - 33, 38, 66, "0_DEVICES", 7, 13)
            _txt(msp, right[i].get("tag", ""), x4 + W - 265, cy, 11)
    _box(msp, x4 + 62, y + P + H * .43, 26, 115, "0_HARDWARE", 7, 18)
    for hy in (y + P + H * .18, y + P + H * .50, y + P + H * .82):
        _hinge(msp, x4 + W, hy)

    # 5. INTERNAL GA
    x5 = x4 + W + gap
    _title(msp, "BO TRI THIET BI", x5, y, W, total_h)
    _cabinet(msp, x5, y, W, H, P)
    plate_x, plate_y = x5 + 35, y + P + 35
    _box(msp, plate_x, plate_y, W - 70, H - 70, "0_PLATE", 7, 25)
    for rail_y in (plate_y + 110, plate_y + H * .60, plate_y + H - 120):
        _line(msp, (plate_x + 15, rail_y), (plate_x + W - 85, rail_y), "0_STIFFENER", 7, 25)
    _perforated_bar(msp, plate_x + 38, plate_y + 120, 24, H - 260, 6, True)
    _perforated_bar(msp, plate_x + W - 132, plate_y + 120, 24, H - 260, 3, True)

    inc_x = x5 + (W - inc_w) / 2
    inc_y = y + P + H * .67
    _breaker(msp, inc_x, inc_y, inc_w, inc_h, incomer.get("tag", "QF0"), incomer.get("part_number") or "MCCB TONG")

    # Incoming conductors: cable entry -> CT -> main breaker.  These are
    # deliberately WIRING, not copper busbars; distribution copper starts only
    # at the load side of the main MCCB as shown in the approved fabrication GA.
    center_x = x5 + W / 2
    phase_colors = [1, 2, 5, 3]
    phase_names = ["R", "S", "T", "N"]
    bar_pitch = 28.0
    bar_xs = [center_x - 1.5 * bar_pitch + i * bar_pitch for i in range(4)]
    cable_top = y + P + H - 55
    for i, (bx, col, phase) in enumerate(zip(bar_xs, phase_colors, phase_names)):
        _txt(msp, phase, bx, cable_top + 18, 12, "0_TEXT", col)
        if i < 3:
            wire_y = cable_top - 24 - i * 9
            _line(msp, (plate_x + 55, wire_y), (bx, wire_y), "0_WIRING", col, 25)
            _line(msp, (bx, wire_y), (bx, inc_y + inc_h), "0_WIRING", col, 25)
            _circle(msp, bx, cable_top - 85, 28, "0_DEVICES", col, 25)
            _circle(msp, bx, cable_top - 85, 13, "0_DEVICES", 7, 18)

    # Main vertical distribution bars and phase taps to both columns.
    bus_top = inc_y - 20
    bus_bottom = y + P + 210
    if draw_busbar:
        for bx, col, phase in zip(bar_xs, phase_colors, phase_names):
            _box(msp, bx - 4, bus_bottom, 8, bus_top - bus_bottom, "0_COPPER", col, 60)
            _txt(msp, phase, bx, bus_bottom - 16, 11, "0_TEXT", col)
        for sy in (bus_bottom + 45, (bus_bottom + bus_top) / 2, bus_top - 45):
            _box(msp, bar_xs[0] - 22, sy - 6, bar_xs[-1] - bar_xs[0] + 44, 12, "0_COPPER_SUPPORT", 6, 30)
            for bx in bar_xs:
                _circle(msp, bx, sy, 4, "0_HARDWARE", 7, 13)

    for i in range(tiers):
        cy = lower_y + i * step
        if i < len(left):
            dev = left[i]
            dw, dh, _ = PhysicalLayoutEngine.get_component_dimensions(dev)
            rw, rh = dh, dw
            bx = x5 + 95
            _breaker(msp, bx, cy - rh / 2, rw, rh, dev.get("tag", f"QF{i+1}"), dev.get("part_number") or f"{int(dev.get('in_a') or 0)}A", True)
            # Each 3-pole outgoing MCCB receives all R/S/T phases.  The small
            # vertical separation keeps the copper routing readable in GA view.
            for phase_idx, (source_x, col) in enumerate(zip(bar_xs[:3], phase_colors[:3])):
                tap_y = cy + (phase_idx - 1) * 7
                _line(msp, (bx + rw, tap_y), (source_x - 7, tap_y), "0_COPPER", col, 35)
        if i < len(right):
            dev = right[i]
            dw, dh, _ = PhysicalLayoutEngine.get_component_dimensions(dev)
            rw, rh = dh, dw
            bx = x5 + W - 95 - rw
            _breaker(msp, bx, cy - rh / 2, rw, rh, dev.get("tag", f"QF{i+7}"), dev.get("part_number") or f"{int(dev.get('in_a') or 0)}A", True)
            for phase_idx, (source_x, col) in enumerate(zip(bar_xs[:3], phase_colors[:3])):
                tap_y = cy + (phase_idx - 1) * 7
                _line(msp, (source_x + 7, tap_y), (bx, tap_y), "0_COPPER", col, 35)

    terminal_y = y + P + 115
    terminal_x = x5 + 95
    terminal_w = W - 190
    for i in range(20):
        _box(msp, terminal_x + i * terminal_w / 20, terminal_y, terminal_w / 20 - 3, 48, "0_DEVICES", 4, 15)
    _box(msp, terminal_x, terminal_y - 45, terminal_w, 12, "0_COPPER", 3, 50)
    _txt(msp, "X1 / PE", x5 + W / 2, terminal_y - 62, 13)

    # 6. SIDE SECTION
    x6 = x5 + W + gap
    _title(msp, "MAT CAT CANH", x6, y, D, total_h)
    _cabinet(msp, x6, y, D, H, P)
    # Back plate, mounting depth, device side profiles, inner cover and door.
    plate_z = x6 + 38
    inner_cover_z = x6 + D - 72
    door_z = x6 + D - 28
    _line(msp, (plate_z, y + P + 35), (plate_z, y + total_h - 35), "0_PLATE", 4, 30)
    _line(msp, (inner_cover_z, y + P + 42), (inner_cover_z, y + total_h - 42), "0_PLATE", 6, 24)
    _line(msp, (door_z, y + P + 35), (door_z, y + total_h - 35), "0_FRAME", 7, 24)
    _box(msp, plate_z, inc_y, min(inc_d, inner_cover_z - plate_z - 12), inc_h, "0_DEVICES", 4, 25)
    _box(msp, plate_z + min(inc_d, inner_cover_z - plate_z - 12) * .35, inc_y + inc_h * .38,
         min(inc_d, inner_cover_z - plate_z - 12) * .35, inc_h * .24, "0_DEVICES", 2, 18)
    for i in range(tiers):
        cy = lower_y + i * step
        dev = (left + right)[min(i, len(left + right) - 1)] if left or right else None
        if dev:
            dw, _, dd = PhysicalLayoutEngine.get_component_dimensions(dev)
            profile_d = min(dd, inner_cover_z - plate_z - 12)
            _box(msp, plate_z, cy - dw / 2, profile_d, dw, "0_DEVICES", 4, 20)
            _box(msp, plate_z + profile_d * .38, cy - dw * .18, profile_d * .32, dw * .36, "0_DEVICES", 7, 13)
    for i, col in enumerate(phase_colors):
        _box(msp, plate_z + 150 + i * 13, bus_bottom, 7, bus_top - bus_bottom, "0_COPPER", col, 50)
    # Cable/CT/main assembly at the top, viewed from the side.
    _line(msp, (plate_z + 15, cable_top - 25), (inner_cover_z - 18, cable_top - 25), "0_WIRING", 1, 22)
    _circle(msp, plate_z + 115, cable_top - 82, 24, "0_DEVICES", 1, 22)
    _circle(msp, plate_z + 115, cable_top - 82, 10, "0_DEVICES", 7, 15)
    for sy in (bus_bottom + 45, (bus_bottom + bus_top) / 2, bus_top - 45):
        _box(msp, plate_z + 135, sy - 5, 85, 10, "0_COPPER_SUPPORT", 6, 24)
    for hy in (y + P + H * .18, y + P + H * .50, y + P + H * .82):
        _hinge(msp, x6 + D, hy)
    _dim_h(msp, x6, y, D, f"{int(D)}")

    # 7/8. BOTTOM AND TOP
    plan_y = y - D - 170
    plan_x1 = x2 + D + gap
    for idx, (name, is_top) in enumerate((("MAT DAY", False), ("MAT NOC", True))):
        px = plan_x1 + idx * (W + 260)
        _txt(msp, name, px + W / 2, plan_y + D + 62, 28, "0_TEXT_TITLE", 1)
        _box(msp, px, plan_y, W, D, "0_FRAME", 7, 35)
        _box(msp, px + 45, plan_y + 35, W - 90, D - 70, "0_PLATE", 7, 20)
        if is_top:
            gland_w = W * .55
            _box(msp, px + (W - gland_w) / 2, plan_y + D * .32, gland_w, D * .36, "0_PLATE", 7, 25)
            _txt(msp, "TAM GLAND CAP VAO/RA", px + W / 2, plan_y + D / 2, 15)
        else:
            _txt(msp, "DAY KIN - LO BAT CHAN DE", px + W / 2, plan_y + D / 2, 15)
        _dim_h(msp, px, plan_y, W, f"{int(W)}")
        _dim_v(msp, px, plan_y, D, f"{int(D)}")

    # Fabrication notes, same visual hierarchy as the approved sample.
    note_x = x1 + 45
    note_y = plan_y + D - 15
    _txt(msp, f"TU DIEN {panel_code}", note_x, note_y, 25, "0_TEXT_TITLE", 6, TextEntityAlignment.MIDDLE_LEFT)
    notes = [
        "SO LUONG: 1 TU",
        f"KT THAN: {int(H)}C x {int(W)}R x {int(D)}S (mm)",
        f"CHAN DE: {int(P)}mm; TONG CAO: {int(total_h)}mm",
        "TU TRONG NHA, DAT TREN DE, 2 LOP CANH",
        f"TON {float(specs.get('thickness') or 1.5):g}mm SON TINH DIEN RAL 7032 SAN",
        "CAP VAO VA CAP RA TU NOC",
        f"THANH CAI: {specs.get('busbar_spec', 'TBD')}",
    ]
    for idx, note in enumerate(notes):
        _txt(msp, note, note_x, note_y - 40 - idx * 38, 17, "0_TEXT_TITLE", 6, TextEntityAlignment.MIDDLE_LEFT)

    # Put a visible warning on the drawing instead of silently accepting an
    # electrically incompatible catalog proxy.
    warnings = (specs.get("fit_check") or {}).get("catalog_warnings") or []
    if warnings:
        _txt(msp, "CANH BAO: MODEL MCCB TONG CHUA DAT Icu - CHI DUNG KICH THUOC PROXY", x5 + W / 2,
             y + P + 70, 13, "0_TEXT_TITLE", 1)
