# ==========================================================================================
# SK120 DIN Rail Card-Slot Enclosure Generator
# Generates enclosure for headless XY-SK120X DC-DC converters
# with ESP32 bay, parametric fan, and power distribution
#
# Layout: Boards lie FLAT (horizontal), stacked VERTICALLY, slide in from FRONT
#
# Coordinate system:
#   X = depth from DIN rail (0 at rail, positive outward/forward)
#   Y = vertical (0 at center, +Y up, -Y down)
#   Z = width along DIN rail (0 at one edge)
#
# Cross-section (looking from side, Z into page):
#
#   +Y (top)
#     ┌──────────────────────┐
#     │  ESP32 bay           │
#     ├──────────────────────┤
#     │  ═══ SK120 #3 ═══   │  ← horizontal board, components up
#     │  --- divider ---     │
#     │  ═══ SK120 #2 ═══   │
#     │  --- divider ---     │
#     │  ═══ SK120 #1 ═══   │
#     ├──────────────────────┤
#     │  WAGO / power in     │
#     └──────────────────────┘
#   -Y (bottom)
#   ←X (rail)          X→ (front, boards slide in)
#
# ==========================================================================================

from din_declarations import *

import cadquery as cq
from cadquery.func import *
from pathlib import Path
import os


def generate_enclosure(c: SK120Config):
    print(f"Generating SK120 enclosure: {c.CONFIG_NAME}")
    print(f"  Enclosure width (Z, along rail): {c.enclosure_width}mm")
    print(f"  Enclosure depth (X, from rail):  {c.enclosure_depth}mm")
    print(f"  Enclosure height (Y, vertical):  {c.enclosure_height}mm")
    print(cq.__version__)

    global case, lid, clips

    EW = c.enclosure_width    # Z axis (along rail) — narrow now (~54mm)
    ED = c.enclosure_depth    # X axis (from rail)  — board length + walls
    EH = c.enclosure_height   # Y axis (vertical)   — stacked boards + ESP32
    CT = c.CASE_THICKNESS
    sk = c.sk120

    # Board slot pitch: each board layer takes this much vertical space
    board_layer_height = sk.component_height + sk.pcb_thickness + c.board_spacing

    # Y positions of each board's PCB bottom surface (component side faces UP)
    # Stack starts from bottom of enclosure, above case wall
    board_y_positions = []
    for i in range(c.num_boards):
        y_bottom = -EH/2 + CT + c.board_spacing + i * board_layer_height
        board_y_positions.append(y_bottom)

    # ESP32 bay starts above the last board's component space
    esp32_y_start = board_y_positions[-1] + sk.pcb_thickness + sk.component_height
    esp32_y_center = (esp32_y_start + EH/2 - CT) / 2

    # DIN rail clip is centered vertically on the enclosure
    # DIN rail standard positions are relative to the clip center
    din_center_y = 0  # center of DIN rail attachment

    # ======================== dummy cutout ==================
    dummy = cq.Workplane("XY").box(0.1, 0.1, 0.1).translate((-0.1, EH/2 - 10, 5))

    # ======================== DIN rail clip ==================
    # Single clip, centered on Z (enclosure is narrow enough for one)

    CLIP_UNIT_WIDTH = EW - 2*CT - 0.2  # fill available width
    CLIP_GAP = 0.1
    CLIP_THICKNESS = 3.5
    CLIP_SLOT_DEPTH = CLIP_THICKNESS
    CLIP_HIDDEN_LENGTH = EH/2 - c.DIN_RAIL_LOWER + CLIP_SLOT_DEPTH
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
    CLIP_CUTOUT_HEIGHT = EH/2 - c.DIN_RAIL_LOWER

    def make_clip(z_pos):
        cw = CLIP_UNIT_WIDTH
        cl = (cq.Workplane("front")
            .moveTo(0, -CLIP_BASE_HEIGHT)
            .hLine(cw / 2.0)
            .vLine(CLIP_LEG_LENGTH + CLIP_BASE_HEIGHT - 2 * CLIP_LEG_RADIUS)
            .threePointArc((cw/2 + CLIP_LEG_RADIUS, CLIP_LEG_LENGTH - CLIP_LEG_RADIUS),
                           (cw/2, CLIP_LEG_LENGTH))
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
            .center(0, (CLIP_THICKNESS - CLIP_SLOT_WIDTH/2 + 0.18))
            .rect(cw + 3, CLIP_SLOT_WIDTH)
            .extrude(-CLIP_SLOT_DEPTH, combine='s', taper=CLIP_SLOT_TAPER)
            .rotate((0, 0, 0), (0, 1, 0), 90)
            .translate((-(CLIP_THICKNESS + CLIP_GAP), -EH/2, z_pos))
        )
        return cl

    def make_clip_cutout(z_pos):
        cw = CLIP_UNIT_WIDTH
        cc = cq.Workplane("XY").box(CLIP_THICKNESS + 2*CLIP_GAP,
                                     CLIP_CUTOUT_HEIGHT,
                                     cw + 2*CLIP_GAP)
        cc = (cc.faces("<X").workplane()
            .center(-CLIP_CUTOUT_HEIGHT/2 + CLIP_UPPER_LOCK, -cw/2)
            .circle(CLIP_LEG_RADIUS + CLIP_GAP)
            .center(0, cw)
            .circle(CLIP_LEG_RADIUS + CLIP_GAP)
            .center(CLIP_LOCK_DISTANCE, 0)
            .circle(CLIP_LEG_RADIUS + CLIP_GAP)
            .center(0, -cw)
            .circle(CLIP_LEG_RADIUS + CLIP_GAP)
            .extrude(-CLIP_THICKNESS - 2*CLIP_GAP)
        )
        cc = cc.translate((-CLIP_THICKNESS/2 - CLIP_GAP,
                           -CLIP_CUTOUT_HEIGHT/2 - c.DIN_RAIL_LOWER,
                           z_pos))
        return cc

    # Single clip centered on Z
    clip_z = EW / 2
    clips = [make_clip(clip_z)]
    clip_cutouts = make_clip_cutout(clip_z)

    # ======================== WAGO fixation parts ==================

    WAGO_FIX_HEIGHT = 2.5
    WAGO_FIX_EXTRUDE = 1.25

    def wago_fix(count, x, y, z):
        wago_span = EW - 4*CT
        wago_221_fix = (cq.Workplane("front")
            .box(wago_span, c.WAGO_FIX_WIDTH, WAGO_FIX_HEIGHT)
            .edges("#X").fillet(0.4))
        wago_fix_cutout = cq.Workplane("front").box(
            wago_span + 4, c.WAGO_FIX_WIDTH + 0.1, WAGO_FIX_HEIGHT + 0.1)
        wago_221_fix = wago_221_fix.center(
            -c.WAGO_OFFSET * (count - 1) / 2, 0).rect(4.0, 2.5).extrude(WAGO_FIX_EXTRUDE * 2)
        for i in range(1, count):
            wago_221_fix = wago_221_fix.center(c.WAGO_OFFSET, 0).rect(4.0, 2.5).extrude(
                WAGO_FIX_EXTRUDE * 2)
        wago_221_fix = wago_221_fix.rotate((0, 0, 0), (0, 1, 0), -90).translate((x, y, z))
        wago_fix_cutout = wago_fix_cutout.rotate((0, 0, 0), (0, 1, 0), -90).translate((x, y, z))
        return wago_221_fix, wago_fix_cutout

    # Internal WAGOs near bottom of enclosure, below board stack
    wago_x_pos = CT + c.WAGO_HEIGHT + WAGO_FIX_HEIGHT/2
    wago_y_pos = -EH/2 + CT + c.WAGO_FIX_WIDTH/2 + 1
    wago_z_pos = EW / 2

    if c.NR_WAGO_INTERNAL > 0:
        internal_wago_fix, internal_wago_fix_cutout = wago_fix(
            c.NR_WAGO_INTERNAL, wago_x_pos, wago_y_pos, wago_z_pos)
    else:
        internal_wago_fix = dummy
        internal_wago_fix_cutout = dummy

    # ======================== Main case body ==================

    BACK_WALL_X = -5  # back wall extends behind rail plane

    sketch_outer = (cq.Sketch()
        .segment((0, c.DIN_RAIL_UPPER), (-0.8, c.DIN_RAIL_UPPER))
        .segment((-3.2, c.DIN_RAIL_UPPER - 3.2))
        .segment((BACK_WALL_X, c.DIN_RAIL_UPPER - 3.2))
        .segment((BACK_WALL_X, EH/2))
        .segment((ED, EH/2))
        .segment((ED, -EH/2))
        .segment((BACK_WALL_X, -EH/2))
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
        .segment((CT, -EH/2 + CT), (CT, EH/2 - CT))
        .segment((ED - CT, EH/2 - CT))
        .segment((ED - CT, -EH/2 + CT))
        .close()
        .assemble(tag="innerface")
        .vertices()
        .fillet(0.6)
        .clean()
    )

    outer = cq.Workplane("XY").placeSketch(sketch_outer).extrude(EW)
    inner = cq.Workplane("XY", (0, 0, EW)).placeSketch(sketch_inner).extrude(-(EW - CT))

    # ======================== Screw blocks ==================

    def case_screw_block(x, y):
        z = EW - 2*CT - c.SCREW_LID_EXTRA
        return (cq.Workplane("XY")
            .box(c.SCREW_BLOCK_SIZE, c.SCREW_BLOCK_SIZE, z)
            .faces(">Z").cboreHole(c.SCREW_HOLE_DIAM, c.SCREW_INSERT_DIAM,
                                    c.SCREW_INSERT_DEPTH, c.SCREW_HOLE_DEPTH)
            .translate((x, y, z/2 + CT))
            .edges("|Z").fillet(1))

    def lid_screw_block(x, y):
        z = CT + c.SCREW_LID_EXTRA
        return (cq.Workplane("XY")
            .box(c.SCREW_BLOCK_SIZE, c.SCREW_BLOCK_SIZE, z)
            .translate((x, y, EW - z/2))
            .edges("|Z").fillet(1))

    screw_margin_x = c.SCREW_BLOCK_SIZE/2 + CT + 1
    screw_margin_y = c.SCREW_BLOCK_SIZE/2 + CT + 1
    screw_positions = [
        (CT + screw_margin_x,  EH/2 - screw_margin_y),
        (ED - screw_margin_x,  EH/2 - screw_margin_y),
        (CT + screw_margin_x, -EH/2 + screw_margin_y),
        (ED - screw_margin_x, -EH/2 + screw_margin_y),
    ]

    case_screw_blocks = [case_screw_block(x, y) for (x, y) in screw_positions]
    lid_screw_blocks  = [lid_screw_block(x, y) for (x, y) in screw_positions]

    # ======================== Card slot shelves and grooves ==================
    # Horizontal divider shelves between boards — boards rest on these
    # Grooves on the side walls (Z=CT and Z=EW-CT) grip PCB edges

    slot_w = sk.pcb_thickness + sk.slot_clearance  # groove width
    inner_width = EW - 2*CT  # internal Z span
    inner_depth = ED - 2*CT  # internal X span

    # Horizontal shelves: thin platforms between each board layer
    shelves = dummy
    for i in range(c.num_boards + 1):
        # Shelf Y position: between boards (or at bottom/top of stack)
        if i == 0:
            shelf_y = board_y_positions[0] - c.board_spacing/2
        elif i == c.num_boards:
            shelf_y = board_y_positions[-1] + sk.pcb_thickness + sk.component_height + c.board_spacing/2
        else:
            shelf_y = (board_y_positions[i-1] + sk.pcb_thickness + sk.component_height
                       + board_y_positions[i]) / 2

        shelf = (cq.Workplane("XY")
            .box(inner_depth, c.board_spacing, inner_width)
            .translate((CT + inner_depth/2, shelf_y, EW/2)))
        shelves = shelves.union(shelf)

    # Grooves on side walls for PCB edges to slide into
    # Each board has a groove on left wall (Z=CT) and right wall (Z=EW-CT)
    # Grooves run in X direction (front-to-back), at the Y height of each board
    slot_cutouts = dummy
    for i in range(c.num_boards):
        pcb_y = board_y_positions[i] + sk.pcb_thickness/2  # center of PCB

        # Left wall groove (low Z side)
        left_groove = (cq.Workplane("XY")
            .box(inner_depth, slot_w, c.slot_depth)
            .translate((CT + inner_depth/2, pcb_y, CT + c.slot_depth/2)))
        # Right wall groove (high Z side)
        right_groove = (cq.Workplane("XY")
            .box(inner_depth, slot_w, c.slot_depth)
            .translate((CT + inner_depth/2, pcb_y, EW - CT - c.slot_depth/2)))

        slot_cutouts = slot_cutouts.union(left_groove).union(right_groove)

    # ======================== ESP32 bay ==================
    # ESP32 sits above the board stack

    esp32_bay_y_center = (esp32_y_start + EH/2 - CT) / 2

    # Mounting carriers for ESP32
    CARRIER_X = 7
    CARRIER_Y = 2
    esp32_carriers = (cq.Workplane("XY")
        .pushPoints([
            (CT + 10, esp32_y_start + CARRIER_Y/2 + 1),
            (CT + 10, esp32_y_start + c.esp32.length - CARRIER_Y/2)
        ])
        .rect(CARRIER_X, CARRIER_Y)
        .extrude(c.esp32.mount_height)
        .translate((0, 0, EW/2 - c.esp32.board_width/2)))

    # USB cutout for ESP32 on front face (X = ED)
    USB_WIDTH = 9.3
    USB_HEIGHT = 3.3
    if c.esp32.usb_height is not None:
        usb_esp32_cutout = (cq.Workplane("ZY",
            (ED,
             esp32_bay_y_center,
             EW/2))
            .moveTo(0, USB_HEIGHT/2)
            .hLine(USB_WIDTH/2 - USB_HEIGHT/2)
            .threePointArc((USB_WIDTH/2, 0), (USB_WIDTH/2 - USB_HEIGHT/2, -USB_HEIGHT/2))
            .hLine(-USB_WIDTH + USB_HEIGHT)
            .threePointArc((-USB_WIDTH/2, 0), (-USB_WIDTH/2 + USB_HEIGHT/2, USB_HEIGHT/2))
            .hLine(USB_WIDTH/2 - USB_HEIGHT/2)
            .close()
            .extrude(-CT - 1, taper=-30))
    else:
        usb_esp32_cutout = dummy

    # Wiring opening between ESP32 bay and top board slot
    wire_opening_y = esp32_y_start
    wire_opening = (cq.Workplane("XY")
        .box(inner_depth * 0.4, c.board_spacing + 2, inner_width * 0.5)
        .translate((CT + inner_depth/2, wire_opening_y, EW/2)))

    # ======================== Fan mount (on lid, rear-biased) ==================
    # Fan is on the lid (Z = EW face), positioned over the board stack, biased toward rear

    fan_x_center = CT + c.fan_offset_from_rear + c.fan.size/2
    # Center the fan vertically on the board stack area
    stack_y_center = (board_y_positions[0] + board_y_positions[-1] + sk.pcb_thickness + sk.component_height) / 2

    fan_cutout = (cq.Workplane("XY", (fan_x_center, stack_y_center, EW))
        .rect(c.fan.size, c.fan.size)
        .extrude(-CT - 2))

    fan_screw_cutout = dummy
    hs = c.fan.screw_spacing / 2
    for dx in [-hs, hs]:
        for dy in [-hs, hs]:
            hole = (cq.Workplane("XY", (fan_x_center + dx, stack_y_center + dy, EW))
                .circle(c.fan.screw_diam / 2)
                .extrude(-CT - 2))
            fan_screw_cutout = fan_screw_cutout.union(hole)

    # ======================== Power input (bottom face) ==================

    pi = c.power_input
    power_in_cutout = (cq.Workplane("XY")
        .box(pi.depth + 2, CT + 2, pi.width + 1)
        .translate((CT + pi.depth/2 + 5, -EH/2, EW/2)))

    # ======================== Power output (top face, one per board) ==================
    # Output terminals on top face, spaced vertically wouldn't make sense now.
    # Instead, outputs go on the FRONT face (X = ED), one per board at each board's Y level.

    po = c.power_output
    power_out_cutouts = dummy
    for i in range(c.num_boards):
        pcb_y = board_y_positions[i] + sk.pcb_thickness/2
        po_cut = (cq.Workplane("XY")
            .box(CT + 2, po.height + 1, po.width + 1)
            .translate((ED, pcb_y + sk.component_height/2, EW/2)))
        power_out_cutouts = power_out_cutouts.union(po_cut)

    # ======================== Ventilation slots ==================

    VENT_WIDTH = 2.0
    VENT_HEIGHT = 15.0
    VENT_SPACING = 4.0
    vent_cutouts = dummy

    # Front face vents (X = ED), above and below board stack
    for vy_offset in [-EH/4, EH/4]:
        vent = (cq.Workplane("XY")
            .box(CT + 2, VENT_HEIGHT, VENT_WIDTH)
            .translate((ED, vy_offset, EW/2)))
        vent_cutouts = vent_cutouts.union(vent)

    # Side face vents (Z = 0, left side wall)
    side_x_start = CT + 10
    side_x_end = ED - CT - 10
    num_side_vents = int((side_x_end - side_x_start) / (VENT_WIDTH + VENT_SPACING))
    for i in range(num_side_vents):
        vx = side_x_start + i * (VENT_WIDTH + VENT_SPACING) + VENT_WIDTH/2
        for board_i in range(c.num_boards):
            vy = board_y_positions[board_i] + sk.pcb_thickness + sk.component_height/2
            vent = (cq.Workplane("XY")
                .box(VENT_WIDTH, sk.component_height * 0.6, CT + 2)
                .translate((vx, vy, 0)))
            vent_cutouts = vent_cutouts.union(vent)

    # ======================== Text/Branding ==================

    text_brand = cq.Workplane("YX").center(0, ED/2).text(c.BRAND, 8, -0.3)

    if c.MODULE_NAME:
        text_name = (cq.Workplane("YZ", (ED, -EH/4, 5))
            .text(c.MODULE_NAME, 6, -0.3, kind="bold", halign="left"))
    else:
        text_name = dummy

    # ======================== Lid ==================
    # Lid covers the Z+ face (side panel)

    lid = (cq.Workplane("XY", (0, 0, EW))
        .placeSketch(sketch_inner.copy().wires().offset(1))
        .extrude(-CT))

    for lb in lid_screw_blocks:
        lid = lid.union(lb, clean=True)

    for (x, y) in screw_positions:
        lid = (lid.faces(">Z").workplane()
            .moveTo(x, y)
            .cboreHole(c.SCREW_HOLE_DIAM + 0.4, c.SCREW_HEAD_DIAM,
                       c.SCREW_HEAD_DEPTH, c.SCREW_HOLE_DEPTH))

    lid = lid.cut(fan_cutout).cut(fan_screw_cutout)

    # ======================== Build case ==================

    case = (outer.cut(inner)
        .cut(clip_cutouts)
        .union(shelves)
        .cut(slot_cutouts)
        .union(esp32_carriers)
        .cut(wire_opening)
        .cut(usb_esp32_cutout)
        .union(internal_wago_fix)
        .cut(internal_wago_fix_cutout)
        .cut(power_in_cutout)
        .cut(power_out_cutouts)
        .cut(vent_cutouts)
        .cut(text_brand)
        .cut(text_name)
        .cut(lid)
    )

    for csb in case_screw_blocks:
        case = case.union(csb)

    case = case.cut(internal_wago_fix_cutout)

    # ================================= Export ======================

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

    basename = Path(os.path.basename(__file__)).stem + "_" + c.CONFIG_NAME
    for name in results:
        print(f"{name}: \n {results[name]} \n ")
        rot = rotations.get(name, ((0, 0, 0), (0, 1, 0), 0))
        trans = translations.get(name, ((0, 0, 0),))
        results[name].rotate(*rot).translate(*trans).export(
            basename + "_" + name + ".stl")

    # Small parts
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

    # STEP assembly
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
