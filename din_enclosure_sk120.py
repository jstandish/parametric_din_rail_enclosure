# ==========================================================================================
# SK120 DIN Rail Card-Slot Enclosure Generator
# Generates enclosure for headless XY-SK120X DC-DC converters
# with ESP32 bay, parametric fan, and power distribution
#
# Coordinate system:
#   X = depth from DIN rail (0 at rail, positive outward/forward)
#   Y = vertical along DIN rail (0 at center, +Y up, -Y down)
#   Z = width along DIN rail (0 at one edge)
# ==========================================================================================

from din_declarations import *

import cadquery as cq
from cadquery.func import *
from pathlib import Path
import os


def generate_enclosure(c: SK120Config):
    print(f"Generating SK120 enclosure: {c.CONFIG_NAME}")
    print(f"  Enclosure width: {c.enclosure_width}mm")
    print(f"  Enclosure depth: {c.enclosure_depth}mm")
    print(f"  DIN height: {c.DIN_HEIGHT}mm")
    print(cq.__version__)

    global case, lid, clips

    EW = c.enclosure_width   # total width along DIN rail (Z axis)
    ED = c.enclosure_depth   # total depth from rail (X axis)
    EH = c.DIN_HEIGHT        # height (Y axis)
    CT = c.CASE_THICKNESS
    sk = c.sk120

    # Card slot zone width (Z) -- just the SK120 section
    card_zone_width = c.num_boards * sk.pcb_width + (c.num_boards + 1) * c.board_spacing
    card_zone_z_start = CT   # Z start of card slot area
    card_zone_z_end = CT + card_zone_width

    # ESP32 bay spans
    esp32_z_start = card_zone_z_end
    esp32_z_end = EW - CT
    esp32_z_center = (esp32_z_start + esp32_z_end) / 2

    # ======================== dummy cutout ==================
    dummy = cq.Workplane("XY").box(0.1, 0.1, 0.1).translate((-0.1, EH / 2 - 10, 5))

    # ======================== DIN rail clips (3 evenly spaced) ==================

    CLIP_UNIT_WIDTH = 14.0   # standard DIN clip width
    CLIP_GAP = 0.1
    CLIP_THICKNESS = 3.5
    CLIP_SLOT_DEPTH = CLIP_THICKNESS
    CLIP_HIDDEN_LENGTH = EH / 2 - c.DIN_RAIL_LOWER + CLIP_SLOT_DEPTH
    CLIP_TOP_HEIGHT = 8
    CLIP_LEG_WIDTH = 2.6
    CLIP_LEG_HEADROOM = 1
    CLIP_LEG_RADIUS = 1.2
    CLIP_LEG_LENGTH = CLIP_HIDDEN_LENGTH - CLIP_TOP_HEIGHT - CLIP_LEG_HEADROOM
    CLIP_LEG_GAP_WIDTH = 1.5
    CLIP_BASE_HEIGHT = 6
    CLIP_CHAMFER = 1.5
    CLIP_UPPER_LOCK = CLIP_TOP_HEIGHT - CLIP_SLOT_DEPTH + CLIP_LEG_HEADROOM + CLIP_LEG_RADIUS
    CLIP_LOCK_DISTANCE = 5
    CLIP_SLOT_WIDTH = 1.4
    CLIP_SLOT_TAPER = 3
    CLIP_CUTOUT_HEIGHT = EH / 2 - c.DIN_RAIL_LOWER

    def make_clip(z_pos):
        """Generate a single DIN rail clip centered at z_pos along the Z axis."""
        cw = CLIP_UNIT_WIDTH
        cl = (cq.Workplane("front")
            .moveTo(0, -CLIP_BASE_HEIGHT)
            .hLine(cw / 2.0)
            .vLine(CLIP_LEG_LENGTH + CLIP_BASE_HEIGHT - 2 * CLIP_LEG_RADIUS)
            .threePointArc((cw / 2 + CLIP_LEG_RADIUS, CLIP_LEG_LENGTH - CLIP_LEG_RADIUS),
                           (cw / 2, CLIP_LEG_LENGTH))
            .hLine(-CLIP_LEG_WIDTH)
            .vLine(-CLIP_LEG_LENGTH)
            .hLine(-CLIP_LEG_GAP_WIDTH)
            .vLine(CLIP_HIDDEN_LENGTH - CLIP_TOP_HEIGHT)
            .hLine(CLIP_LEG_GAP_WIDTH + CLIP_LEG_WIDTH)
            .vLine(CLIP_TOP_HEIGHT)
            .hLine(-cw / 2)
            .mirrorY()
            .moveTo(0, -3)
            .rect(6, 2)
            .extrude(CLIP_THICKNESS)
            .edges(">(0, 1, -1)").chamfer(CLIP_CHAMFER)
            .edges("|Z").fillet(0.5)
            .faces(">Y").workplane()
            .center(0, (CLIP_THICKNESS - CLIP_SLOT_WIDTH / 2 + 0.18))
            .rect(cw + 3, CLIP_SLOT_WIDTH)
            .extrude(-CLIP_SLOT_DEPTH, combine='s', taper=CLIP_SLOT_TAPER)
            .rotate((0, 0, 0), (0, 1, 0), 90)
            .translate((-(CLIP_THICKNESS + CLIP_GAP), -EH / 2, z_pos))
        )
        return cl

    def make_clip_cutout(z_pos):
        """Generate clip cutout at z_pos."""
        cw = CLIP_UNIT_WIDTH
        cc = cq.Workplane("XY").box(CLIP_THICKNESS + 2 * CLIP_GAP,
                                     CLIP_CUTOUT_HEIGHT,
                                     cw + 2 * CLIP_GAP)
        cc = (cc.faces("<X").workplane()
            .center(-CLIP_CUTOUT_HEIGHT / 2 + CLIP_UPPER_LOCK, -cw / 2)
            .circle(CLIP_LEG_RADIUS + CLIP_GAP)
            .center(0, cw)
            .circle(CLIP_LEG_RADIUS + CLIP_GAP)
            .center(CLIP_LOCK_DISTANCE, 0)
            .circle(CLIP_LEG_RADIUS + CLIP_GAP)
            .center(0, -cw)
            .circle(CLIP_LEG_RADIUS + CLIP_GAP)
            .extrude(-CLIP_THICKNESS - 2 * CLIP_GAP)
        )
        cc = cc.translate((-CLIP_THICKNESS / 2 - CLIP_GAP,
                           -CLIP_CUTOUT_HEIGHT / 2 - c.DIN_RAIL_LOWER,
                           z_pos))
        return cc

    # Place 3 clips evenly along the enclosure width
    num_clips = 3
    clip_positions = [EW * (i + 1) / (num_clips + 1) for i in range(num_clips)]

    clips = []
    clip_cutouts = dummy
    for zp in clip_positions:
        clips.append(make_clip(zp))
        clip_cutouts = clip_cutouts.union(make_clip_cutout(zp))

    # ======================== WAGO fixation parts ==================

    WAGO_FIX_HEIGHT = 2.5
    WAGO_FIX_EXTRUDE = 1.25

    def wago_fix(count, x, y, z):
        """Create WAGO 221 holder blocks. Reuses pattern from din_enclosure.py."""
        wago_width_span = card_zone_width * 0.6  # fit within card zone
        wago_221_fix = (cq.Workplane("front")
            .box(wago_width_span, c.WAGO_FIX_WIDTH, WAGO_FIX_HEIGHT)
            .edges("#X").fillet(0.4))
        wago_fix_cutout = cq.Workplane("front").box(
            wago_width_span + 4, c.WAGO_FIX_WIDTH + 0.1, WAGO_FIX_HEIGHT + 0.1)
        wago_221_fix = wago_221_fix.center(
            -c.WAGO_OFFSET * (count - 1) / 2, 0).rect(4.0, 2.5).extrude(WAGO_FIX_EXTRUDE * 2)
        for i in range(1, count):
            wago_221_fix = wago_221_fix.center(c.WAGO_OFFSET, 0).rect(4.0, 2.5).extrude(
                WAGO_FIX_EXTRUDE * 2)
        wago_221_fix = wago_221_fix.rotate((0, 0, 0), (0, 1, 0), -90).translate((x, y, z))
        wago_fix_cutout = wago_fix_cutout.rotate((0, 0, 0), (0, 1, 0), -90).translate((x, y, z))
        return wago_221_fix, wago_fix_cutout

    # Position WAGOs between power input and card slots, near bottom
    wago_x_pos = CT + c.WAGO_HEIGHT + WAGO_FIX_HEIGHT / 2
    wago_y_pos = -EH / 2 + CT + c.WAGO_FIX_WIDTH / 2 + 2
    wago_z_pos = card_zone_z_start + card_zone_width / 2

    if c.NR_WAGO_INTERNAL > 0:
        internal_wago_fix, internal_wago_fix_cutout = wago_fix(
            c.NR_WAGO_INTERNAL, wago_x_pos, wago_y_pos, wago_z_pos)
    else:
        internal_wago_fix = dummy
        internal_wago_fix_cutout = dummy

    # ======================== Main case body ==================

    BACK_WALL_X = -5  # back wall extends behind rail plane

    sketch_outer = (cq.Sketch()
        # Start at top DIN rail notch, go counter-clockwise
        .segment((0, c.DIN_RAIL_UPPER), (-0.8, c.DIN_RAIL_UPPER))
        .segment((-3.2, c.DIN_RAIL_UPPER - 3.2))
        .segment((BACK_WALL_X, c.DIN_RAIL_UPPER - 3.2))
        # Up to top
        .segment((BACK_WALL_X, EH / 2))
        # Across top to front
        .segment((ED, EH / 2))
        # Down the front
        .segment((ED, -EH / 2))
        # Across bottom to back
        .segment((BACK_WALL_X, -EH / 2))
        # Back wall lower DIN rail notch
        .segment((BACK_WALL_X, -c.DIN_RAIL_LOWER + 3.2))
        .segment((-3.2, -c.DIN_RAIL_LOWER + 3.2))
        .segment((-0.8, -c.DIN_RAIL_LOWER))
        .segment((0, -c.DIN_RAIL_LOWER))
        .close()
        .assemble(tag="outerface")
        .edges("|Z" and "<X", tag="outerface")
        .vertices()
        .fillet(0.5)
        .edges("|Z" and ">X", tag="outerface")
        .vertices()
        .fillet(1.5)
        .clean()
    )

    sketch_inner = (cq.Sketch()
        .segment((CT, -EH / 2 + CT), (CT, EH / 2 - CT))
        .segment((ED - CT, EH / 2 - CT))
        .segment((ED - CT, -EH / 2 + CT))
        .close()
        .assemble(tag="innerface")
        .vertices()
        .fillet(0.6)
        .clean()
    )

    outer = cq.Workplane("XY").placeSketch(sketch_outer).extrude(EW)
    inner = cq.Workplane("XY", (0.0, 0.0, EW)).placeSketch(sketch_inner).extrude(-(EW - CT))

    # ======================== Screw blocks ==================

    def case_screw_block(x, y):
        z = EW - 2 * CT - c.SCREW_LID_EXTRA
        return (cq.Workplane("XY")
            .box(c.SCREW_BLOCK_SIZE, c.SCREW_BLOCK_SIZE, z)
            .faces(">Z").cboreHole(c.SCREW_HOLE_DIAM, c.SCREW_INSERT_DIAM,
                                    c.SCREW_INSERT_DEPTH, c.SCREW_HOLE_DEPTH)
            .translate((x, y, z / 2 + CT))
            .edges("|Z").fillet(1))

    def lid_screw_block(x, y):
        z = CT + c.SCREW_LID_EXTRA
        return (cq.Workplane("XY")
            .box(c.SCREW_BLOCK_SIZE, c.SCREW_BLOCK_SIZE, z)
            .translate((x, y, EW - z / 2))
            .edges("|Z").fillet(1))

    # 6 screw positions: 4 corners + 2 mid-span for wide enclosure
    screw_margin_x = c.SCREW_BLOCK_SIZE / 2 + CT + 1
    screw_margin_y = c.SCREW_BLOCK_SIZE / 2 + CT + 1
    screw_positions = [
        (CT + screw_margin_x, EH / 2 - screw_margin_y),
        (ED - screw_margin_x, EH / 2 - screw_margin_y),
        (CT + screw_margin_x, -EH / 2 + screw_margin_y),
        (ED - screw_margin_x, -EH / 2 + screw_margin_y),
    ]

    case_screw_blocks = [case_screw_block(x, y) for (x, y) in screw_positions]
    lid_screw_blocks = [lid_screw_block(x, y) for (x, y) in screw_positions]

    # ======================== Card slot dividers ==================

    slot_w = sk.pcb_thickness + sk.slot_clearance   # groove width for PCB edge
    divider_depth = ED - 2 * CT                      # X extent of dividers
    divider_height = EH - 2 * CT                     # Y extent of dividers

    # Build num_boards + 1 divider walls
    dividers = dummy
    for i in range(c.num_boards + 1):
        # Z center of this divider
        z_pos = card_zone_z_start + i * sk.pcb_width + (i + 0.5) * c.board_spacing
        divider = (cq.Workplane("XY")
            .box(divider_depth, divider_height, c.board_spacing)
            .translate((CT + divider_depth / 2, 0, z_pos)))
        dividers = dividers.union(divider)

    # Cut grooves (slot channels) into divider faces for PCB edges
    # Grooves run vertically (full Y height), at back of enclosure (low X), slot_depth deep
    slot_cutouts = dummy
    for i in range(c.num_boards):
        # Board i sits between divider i and divider i+1
        # Groove on right face of divider i (high-Z side)
        z_left_div = card_zone_z_start + i * sk.pcb_width + (i + 0.5) * c.board_spacing
        groove_z_right = z_left_div + c.board_spacing / 2 - slot_w / 2
        left_groove = (cq.Workplane("XY")
            .box(c.slot_depth, divider_height, slot_w)
            .translate((CT + c.slot_depth / 2, 0, groove_z_right)))
        slot_cutouts = slot_cutouts.union(left_groove)

        # Groove on left face of divider i+1 (low-Z side)
        z_right_div = card_zone_z_start + (i + 1) * sk.pcb_width + (i + 1 + 0.5) * c.board_spacing
        groove_z_left = z_right_div - c.board_spacing / 2 + slot_w / 2
        right_groove = (cq.Workplane("XY")
            .box(c.slot_depth, divider_height, slot_w)
            .translate((CT + c.slot_depth / 2, 0, groove_z_left)))
        slot_cutouts = slot_cutouts.union(right_groove)

    # Bottom shelf/stop in each bay so boards rest at correct height
    shelves = dummy
    shelf_thickness = CT  # thin ledge
    for i in range(c.num_boards):
        bay_z = card_zone_z_start + c.board_spacing + i * (sk.pcb_width + c.board_spacing) + sk.pcb_width / 2
        shelf = (cq.Workplane("XY")
            .box(c.slot_depth, shelf_thickness, sk.pcb_width - 2 * slot_w)
            .translate((CT + c.slot_depth / 2,
                        -EH / 2 + CT + shelf_thickness / 2,
                        bay_z)))
        shelves = shelves.union(shelf)

    # ======================== ESP32 bay ==================

    # ESP32 mounting carriers (small support blocks)
    CARRIER_X = 7
    CARRIER_Y = 2
    esp32_carriers = (cq.Workplane("XY", (0, 0, esp32_z_start))
        .pushPoints([
            (CT + c.esp32.board_width / 2 + 5, -EH / 2 + CT + CARRIER_Y / 2 + 1),
            (CT + c.esp32.board_width / 2 + 5, -EH / 2 + CT + c.esp32.length - CARRIER_Y / 2)
        ])
        .rect(CARRIER_X, CARRIER_Y)
        .extrude(c.esp32.mount_height))

    # USB cutout on top face for ESP32
    USB_WIDTH = 9.3
    USB_HEIGHT = 3.3
    if c.esp32.usb_height is not None:
        usb_esp32_cutout = (cq.Workplane("XZ",
            (CT + c.esp32.board_width / 2 + c.esp32.usb_offset + 5,
             EH / 2,
             esp32_z_center))
            .moveTo(0, USB_HEIGHT / 2)
            .hLine(USB_WIDTH / 2 - USB_HEIGHT / 2)
            .threePointArc((USB_WIDTH / 2, 0), (USB_WIDTH / 2 - USB_HEIGHT / 2, -USB_HEIGHT / 2))
            .hLine(-USB_WIDTH + USB_HEIGHT)
            .threePointArc((-USB_WIDTH / 2, 0), (-USB_WIDTH / 2 + USB_HEIGHT / 2, USB_HEIGHT / 2))
            .hLine(USB_WIDTH / 2 - USB_HEIGHT / 2)
            .close()
            .extrude(CT + 1, taper=-30))
    else:
        usb_esp32_cutout = dummy

    # Wiring opening in the divider between ESP32 bay and last SK120 slot
    last_divider_z = card_zone_z_start + c.num_boards * sk.pcb_width + (c.num_boards + 0.5) * c.board_spacing
    wire_opening = (cq.Workplane("XY")
        .box(divider_depth * 0.5, EH * 0.3, c.board_spacing + 2)
        .translate((CT + divider_depth / 2, 0, last_divider_z)))

    # ======================== Fan mount (on lid, rear-biased) ==================

    fan_x_center = CT + c.fan_offset_from_rear + c.fan.size / 2
    fan_z_center = card_zone_z_start + card_zone_width / 2

    # Fan square cutout through lid
    fan_cutout = (cq.Workplane("XY", (fan_x_center, EH / 2, fan_z_center))
        .rect(c.fan.size, c.fan.size)
        .extrude(-CT - 2))

    # Fan screw holes
    fan_screw_cutout = dummy
    hs = c.fan.screw_spacing / 2
    for dx in [-hs, hs]:
        for dz in [-hs, hs]:
            hole = (cq.Workplane("XY", (fan_x_center + dx, EH / 2, fan_z_center + dz))
                .circle(c.fan.screw_diam / 2)
                .extrude(-CT - 2))
            fan_screw_cutout = fan_screw_cutout.union(hole)

    # ======================== Power input (bottom face) ==================

    pi = c.power_input
    power_in_z = card_zone_z_start + card_zone_width / 2
    power_in_cutout = (cq.Workplane("XY")
        .box(pi.depth + 2, CT + 2, pi.width + 1)
        .translate((CT + pi.depth / 2 + 5, -EH / 2, power_in_z)))

    # ======================== Power output (top face, one per board) ==================

    po = c.power_output
    power_out_cutouts = dummy
    for i in range(c.num_boards):
        bay_z = card_zone_z_start + c.board_spacing + i * (sk.pcb_width + c.board_spacing) + sk.pcb_width / 2
        po_cut = (cq.Workplane("XY")
            .box(po.depth + 2, CT + 2, po.width + 1)
            .translate((CT + po.depth / 2 + 5, EH / 2, bay_z)))
        power_out_cutouts = power_out_cutouts.union(po_cut)

    # ======================== Ventilation slots ==================

    VENT_WIDTH = 2.0
    VENT_HEIGHT = 15.0
    VENT_SPACING = 4.0

    vent_cutouts = dummy

    # Front face vents (at X = ED)
    vent_z_start = card_zone_z_start + 8
    vent_z_end = card_zone_z_end - 8
    num_front_vents = int((vent_z_end - vent_z_start) / (VENT_WIDTH + VENT_SPACING))
    for i in range(num_front_vents):
        vz = vent_z_start + i * (VENT_WIDTH + VENT_SPACING) + VENT_WIDTH / 2
        vent = (cq.Workplane("XY")
            .box(CT + 2, VENT_HEIGHT, VENT_WIDTH)
            .translate((ED, 0, vz)))
        vent_cutouts = vent_cutouts.union(vent)

    # Side face vents (at Z = CT/2, the card-slot side wall)
    side_vent_x_start = CT + 10
    side_vent_x_end = ED - CT - 10
    num_side_vents = int((side_vent_x_end - side_vent_x_start) / (VENT_WIDTH + VENT_SPACING))
    for i in range(num_side_vents):
        vx = side_vent_x_start + i * (VENT_WIDTH + VENT_SPACING) + VENT_WIDTH / 2
        vent = (cq.Workplane("XY")
            .box(VENT_WIDTH, VENT_HEIGHT, CT + 2)
            .translate((vx, 0, CT / 2)))
        vent_cutouts = vent_cutouts.union(vent)

    # ======================== Text/Branding ==================

    text_brand = cq.Workplane("YX").center(0, ED / 2).text(c.BRAND, 8, -0.3)

    if c.MODULE_NAME:
        text_name = (cq.Workplane("YZ", (ED, -c.DIN_NARROW_HEIGHT / 2 + 2.5, 5))
            .text(c.MODULE_NAME, 6, -0.3, kind="bold", halign="left"))
    else:
        text_name = dummy

    # ======================== Lid ==================

    lid = (cq.Workplane("XY", (0, 0, EW))
        .placeSketch(sketch_inner.copy().wires().offset(1))
        .extrude(-CT))

    # Add lid screw blocks
    for lb in lid_screw_blocks:
        lid = lid.union(lb, clean=True)

    # Drill lid screw holes
    for (x, y) in screw_positions:
        lid = (lid.faces(">Z").workplane()
            .moveTo(x, y)
            .cboreHole(c.SCREW_HOLE_DIAM + 0.4, c.SCREW_HEAD_DIAM,
                       c.SCREW_HEAD_DEPTH, c.SCREW_HOLE_DEPTH))

    # Cut fan features from lid
    lid = lid.cut(fan_cutout).cut(fan_screw_cutout)

    # Cut power output terminals and USB from lid (top face)
    lid = lid.cut(power_out_cutouts).cut(usb_esp32_cutout)

    # ======================== Build case ==================

    case = (outer.cut(inner)
        # DIN rail clip cutouts
        .cut(clip_cutouts)
        # Card slot dividers
        .union(dividers)
        .cut(slot_cutouts)
        .union(shelves)
        # ESP32 bay
        .union(esp32_carriers)
        .cut(wire_opening)
        .cut(usb_esp32_cutout)
        # Internal WAGO holders
        .union(internal_wago_fix)
        .cut(internal_wago_fix_cutout)
        # Power cutouts
        .cut(power_in_cutout)
        .cut(power_out_cutouts)
        # Ventilation
        .cut(vent_cutouts)
        # Text
        .cut(text_brand)
        .cut(text_name)
        # Remove lid volume from case
        .cut(lid)
    )

    # Add case screw blocks
    for csb in case_screw_blocks:
        case = case.union(csb)

    # Cut WAGO fixation cutout from case (after screw blocks to avoid interference)
    case = case.cut(internal_wago_fix_cutout)

    # ================================= Final packaging ======================

    results = {
        "case": case,
        "lid": lid,
        "internal_wago_fix": internal_wago_fix,
    }
    for i, cl in enumerate(clips):
        results[f"clip_{i}"] = cl

    rotations = {
        "case": ((0, 0, 0), (0, 1, 0), 0),
        "lid": ((0, 0, 0), (0, 1, 0), 180),
        "internal_wago_fix": ((0, 0, 0), (0, 1, 0), 90),
    }
    for i in range(len(clips)):
        rotations[f"clip_{i}"] = ((0, 0, 0), (0, 1, 0), -90)

    translations = {
        "case": ((0, 0, 0),),
        "lid": ((0, 0, 0),),
        "internal_wago_fix": ((0, 80, 0),),
    }
    for i in range(len(clips)):
        translations[f"clip_{i}"] = ((0, 60 + i * 20, 0),)

    # Export individual STL files
    basename = Path(os.path.basename(__file__)).stem + "_" + c.CONFIG_NAME
    for name in results:
        print(f"{name}: \n {results[name]} \n ")
        rot = rotations.get(name, ((0, 0, 0), (0, 1, 0), 0))
        trans = translations.get(name, ((0, 0, 0),))
        results[name].rotate(*rot).translate(*trans).export(
            basename + "_" + name + ".stl")

    # Arrange small parts for printing
    clip_parts = []
    for i, cl in enumerate(clips):
        cl_r = cl.rotate(*rotations[f"clip_{i}"])
        cl_z = cl_r.val().BoundingBox().zmin
        clip_parts.append(cl_r.translate((0, 40 + i * 20, -cl_z)))

    if len(clip_parts) > 0:
        small_assy = cq.Assembly(clip_parts[0])
        for cp in clip_parts[1:]:
            small_assy = small_assy.add(cp)
        if c.NR_WAGO_INTERNAL > 0:
            wfix_r = internal_wago_fix.rotate(*rotations["internal_wago_fix"])
            wfix_z = wfix_r.val().BoundingBox().zmin
            small_assy = small_assy.add(wfix_r.translate((0, -20, -wfix_z)))
        small_parts = small_assy.toCompound()
        small_parts.export(basename + "_small_parts.stl")

    # Export STEP assembly
    result = cq.Assembly(case).add(lid)
    for cl in clips:
        result = result.add(cl)
    if c.NR_WAGO_INTERNAL > 0:
        result = result.add(internal_wago_fix)

    result.export(basename + "_assbly.step")

    compound = result.toCompound()
    compound.export(basename + "_compound.step")

    print(f"Export complete: {basename}")


def show():
    show_object(case)
    show_object(lid.translate((0, 0, 50)))
    for cl in clips:
        show_object(cl)
