# ==========================================================================================
# SK120 DIN Rail Card-Slot Enclosure Generator
# Bernic High/Low style: two-piece (base + front cover)
#
# Coordinate system:
#   X = depth from DIN rail (0 at rail, positive outward/forward)
#   Y = vertical (0 at center of base, +Y up, -Y down)
#   Z = width along DIN rail (0 at one edge)
#
# Side cross-section (XY plane):
#
#        ┌──── 6-port output terminal (3 pairs +/-)
#        │
#   ┌────┴───┬──────────────┐ ← cover top
#   │  BASE  │  FRONT COVER │
#   │ (low)  │  (high)      │
#   │        │  electronics │
#   │ SK120  │  bay (ESP32) │
#   │ boards │  + fan       │
#   │ in     │              │
#   │ card   │              │
#   │ slots  │              │
#   │        │              │
#   └────┬───┴──────────────┘ ← cover bottom
#        │
#        └──── 2-port input terminal
#   ══DIN══
#   rail
#   ← back        front →
#   X=0            X=total_depth
#
# The BASE clips onto the DIN rail and holds the SK120 boards in card slots.
# The FRONT COVER compression-fits over the base from the front, creating
# the "high" electronics bay for the ESP32 and fan.
# ==========================================================================================

from din_declarations import *

import cadquery as cq
from cadquery.func import *
from pathlib import Path
import os


def generate_enclosure(c: SK120Config):
    EW = c.enclosure_width    # Z (along rail)
    BD = c.base_depth         # X (base only)
    TD = c.total_depth        # X (base + cover)
    EH = c.enclosure_height   # Y (vertical)
    CT = c.CASE_THICKNESS
    sk = c.sk120
    CD = c.COVER_DEPTH        # front cover extension beyond base
    CL = c.COMPRESSION_LIP
    CG = c.COMPRESSION_GAP

    print(f"Generating SK120 enclosure: {c.CONFIG_NAME}")
    print(f"  Width along rail (Z):  {EW}mm")
    print(f"  Base depth (X):        {BD}mm")
    print(f"  Cover depth (X):       {CD}mm")
    print(f"  Total depth (X):       {TD}mm")
    print(f"  Height (Y):            {EH}mm")
    print(cq.__version__)

    global base, cover, clips

    # Board slot pitch: vertical space per board layer
    board_layer_height = sk.component_height + sk.pcb_thickness + c.board_spacing

    # Y positions of each board's PCB bottom surface (components face UP)
    board_y_positions = []
    for i in range(c.num_boards):
        y_bottom = -EH/2 + CT + c.board_spacing + i * board_layer_height
        board_y_positions.append(y_bottom)

    # ======================== dummy cutout ==================
    dummy = cq.Workplane("XY").box(0.1, 0.1, 0.1).translate((-0.1, EH/2 - 10, 5))

    # ======================== DIN rail clip ==================

    CLIP_WIDTH = EW - 2*CT - 0.2
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

    clip_z = EW / 2

    clip = (cq.Workplane("front")
        .moveTo(0, -CLIP_BASE_HEIGHT)
        .hLine(CLIP_WIDTH / 2.0)
        .vLine(CLIP_LEG_LENGTH + CLIP_BASE_HEIGHT - 2 * CLIP_LEG_RADIUS)
        .threePointArc((CLIP_WIDTH/2 + CLIP_LEG_RADIUS, CLIP_LEG_LENGTH - CLIP_LEG_RADIUS),
                       (CLIP_WIDTH/2, CLIP_LEG_LENGTH))
        .hLine(-CLIP_LEG_WIDTH)
        .vLine(-CLIP_LEG_LENGTH)
        .hLine(-CLIP_LEG_GAP_WIDTH)
        .vLine(CLIP_HIDDEN_LENGTH - CLIP_TOP_HEIGHT)
        .hLine(CLIP_LEG_GAP_WIDTH + CLIP_LEG_WIDTH)
        .vLine(CLIP_TOP_HEIGHT)
        .hLine(-CLIP_WIDTH / 2)
        .mirrorY()
        .moveTo(0, -3)
        .rect(6, 2)
        .extrude(CLIP_THICKNESS)
        .edges(">(0, 1, -1)").chamfer(CLIP_CHAMFER)
        .edges("|Z").fillet(0.5)
        .faces(">Y").workplane()
        .center(0, (CLIP_THICKNESS - CLIP_SLOT_WIDTH/2 + 0.18))
        .rect(CLIP_WIDTH + 3, CLIP_SLOT_WIDTH)
        .extrude(-CLIP_SLOT_DEPTH, combine='s', taper=CLIP_SLOT_TAPER)
        .rotate((0, 0, 0), (0, 1, 0), 90)
        .translate((-(CLIP_THICKNESS + CLIP_GAP), -EH/2, clip_z))
    )

    clip_cutout = cq.Workplane("XY").box(CLIP_THICKNESS + 2*CLIP_GAP,
                                          CLIP_CUTOUT_HEIGHT,
                                          CLIP_WIDTH + 2*CLIP_GAP)
    clip_cutout = (clip_cutout.faces("<X").workplane()
        .center(-CLIP_CUTOUT_HEIGHT/2 + CLIP_UPPER_LOCK, -CLIP_WIDTH/2)
        .circle(CLIP_LEG_RADIUS + CLIP_GAP)
        .center(0, CLIP_WIDTH)
        .circle(CLIP_LEG_RADIUS + CLIP_GAP)
        .center(CLIP_LOCK_DISTANCE, 0)
        .circle(CLIP_LEG_RADIUS + CLIP_GAP)
        .center(0, -CLIP_WIDTH)
        .circle(CLIP_LEG_RADIUS + CLIP_GAP)
        .extrude(-CLIP_THICKNESS - 2*CLIP_GAP)
    )
    clip_cutout = clip_cutout.translate((-CLIP_THICKNESS/2 - CLIP_GAP,
                                         -CLIP_CUTOUT_HEIGHT/2 - c.DIN_RAIL_LOWER,
                                         clip_z))
    clips = [clip]

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

    wago_x = CT + c.WAGO_HEIGHT + WAGO_FIX_HEIGHT/2
    wago_y = -EH/2 + CT + c.WAGO_FIX_WIDTH/2 + 1
    wago_z = EW / 2

    if c.NR_WAGO_INTERNAL > 0:
        internal_wago_fix, internal_wago_fix_cutout = wago_fix(
            c.NR_WAGO_INTERNAL, wago_x, wago_y, wago_z)
    else:
        internal_wago_fix = dummy
        internal_wago_fix_cutout = dummy

    # ================================================================
    #                         BASE PART
    # The base clips onto the DIN rail and holds the SK120 boards
    # in horizontal card slots. Terminal blocks on top and bottom.
    # Profile: "low" side — back portion of the stair-step.
    # ================================================================

    BACK_WALL_X = -5  # back wall extends behind rail for DIN clip

    # Base outer profile (XY cross-section, extruded along Z)
    base_sketch_outer = (cq.Sketch()
        .segment((0, c.DIN_RAIL_UPPER), (-0.8, c.DIN_RAIL_UPPER))
        .segment((-3.2, c.DIN_RAIL_UPPER - 3.2))
        .segment((BACK_WALL_X, c.DIN_RAIL_UPPER - 3.2))
        .segment((BACK_WALL_X, EH/2))
        .segment((BD, EH/2))        # base front wall (where cover attaches)
        .segment((BD, -EH/2))
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

    base_sketch_inner = (cq.Sketch()
        .segment((CT, -EH/2 + CT), (CT, EH/2 - CT))
        .segment((BD - CT, EH/2 - CT))
        .segment((BD - CT, -EH/2 + CT))
        .close()
        .assemble(tag="innerface")
        .vertices()
        .fillet(0.6)
        .clean()
    )

    base_outer = cq.Workplane("XY").placeSketch(base_sketch_outer).extrude(EW)
    base_inner = cq.Workplane("XY", (0, 0, EW)).placeSketch(base_sketch_inner).extrude(-(EW - CT))

    # Compression fit lip on base front edge — raised rim that cover grips over
    lip_inner_w = EW - 2*CT
    lip_inner_h = EH - 2*CT
    compression_lip = (cq.Workplane("XY", (BD - CT, 0, EW/2))
        .box(CL, lip_inner_h - 2*CG, lip_inner_w - 2*CG))

    # ======================== Card slot shelves and grooves ==================

    slot_w = sk.pcb_thickness + sk.slot_clearance
    inner_depth = BD - 2*CT
    inner_width = EW - 2*CT

    # Horizontal shelves between board layers
    shelves = dummy
    for i in range(c.num_boards + 1):
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

    # Grooves on side walls for PCB edges
    slot_cutouts = dummy
    for i in range(c.num_boards):
        pcb_y = board_y_positions[i] + sk.pcb_thickness/2

        left_groove = (cq.Workplane("XY")
            .box(inner_depth, slot_w, c.slot_depth)
            .translate((CT + inner_depth/2, pcb_y, CT + c.slot_depth/2)))
        right_groove = (cq.Workplane("XY")
            .box(inner_depth, slot_w, c.slot_depth)
            .translate((CT + inner_depth/2, pcb_y, EW - CT - c.slot_depth/2)))

        slot_cutouts = slot_cutouts.union(left_groove).union(right_groove)

    # ======================== Terminal block cutouts ==================

    # Top: 6-port output terminal (3 pairs of +/-)
    po = c.power_output
    top_terminal_cutout = (cq.Workplane("XY")
        .box(po.depth + 2, CT + 2, po.width + 1)
        .translate((CT + po.depth/2 + 3, EH/2, EW/2)))

    # Bottom: 2-port input terminal
    pi = c.power_input
    bottom_terminal_cutout = (cq.Workplane("XY")
        .box(pi.depth + 2, CT + 2, pi.width + 1)
        .translate((CT + pi.depth/2 + 3, -EH/2, EW/2)))

    # ======================== Base ventilation ==================

    VENT_WIDTH = 2.0
    VENT_SPACING = 4.0
    base_vents = dummy

    # Side vents on left wall (Z = 0) — one row per board layer
    side_x_start = CT + 10
    side_x_end = BD - CT - 10
    num_side_vents = int((side_x_end - side_x_start) / (VENT_WIDTH + VENT_SPACING))
    for i in range(num_side_vents):
        vx = side_x_start + i * (VENT_WIDTH + VENT_SPACING) + VENT_WIDTH/2
        for bi in range(c.num_boards):
            vy = board_y_positions[bi] + sk.pcb_thickness + sk.component_height/2
            vent = (cq.Workplane("XY")
                .box(VENT_WIDTH, sk.component_height * 0.5, CT + 2)
                .translate((vx, vy, 0)))
            base_vents = base_vents.union(vent)

    # ======================== Text/Branding on base ==================

    text_brand = cq.Workplane("YX").center(0, BD/2).text(c.BRAND, 8, -0.3)
    if c.MODULE_NAME:
        text_name = (cq.Workplane("YZ", (BD, -EH/4, 5))
            .text(c.MODULE_NAME, 6, -0.3, kind="bold", halign="left"))
    else:
        text_name = dummy

    # ======================== Build BASE ==================

    base = (base_outer.cut(base_inner)
        .cut(clip_cutout)
        .union(shelves)
        .cut(slot_cutouts)
        .union(compression_lip)
        .union(internal_wago_fix)
        .cut(internal_wago_fix_cutout)
        .cut(top_terminal_cutout)
        .cut(bottom_terminal_cutout)
        .cut(base_vents)
        .cut(text_brand)
        .cut(text_name)
    )

    # ================================================================
    #                       FRONT COVER
    # Compression-fits over the base from the front.
    # Creates the "high" portion of the stair-step profile.
    # Contains the ESP32 electronics bay, fan mount, and wiring space.
    # ================================================================

    # Cover outer dimensions: extends from base front face forward
    cover_x_start = BD - CT  # overlaps base wall slightly for fit
    cover_x_end = TD

    # Cover outer profile (XY, extruded along Z)
    cover_sketch_outer = (cq.Sketch()
        .segment((cover_x_start, -EH/2), (cover_x_start, EH/2))
        .segment((cover_x_end, EH/2))
        .segment((cover_x_end, -EH/2))
        .close()
        .assemble(tag="coverface")
        .vertices()
        .fillet(1.5)
        .clean()
    )

    cover_sketch_inner = (cq.Sketch()
        .segment((cover_x_start + CT, -EH/2 + CT),
                 (cover_x_start + CT, EH/2 - CT))
        .segment((cover_x_end - CT, EH/2 - CT))
        .segment((cover_x_end - CT, -EH/2 + CT))
        .close()
        .assemble(tag="coverin")
        .vertices()
        .fillet(0.6)
        .clean()
    )

    cover_outer = cq.Workplane("XY").placeSketch(cover_sketch_outer).extrude(EW)
    cover_inner = cq.Workplane("XY", (0, 0, EW)).placeSketch(cover_sketch_inner).extrude(-(EW - CT))

    # Compression fit channel — groove inside cover back wall that grips base lip
    comp_channel = (cq.Workplane("XY", (BD - CT - CL/2, 0, EW/2))
        .box(CL + CG, EH - 2*CT - CG, EW - 2*CT - CG))

    # ESP32 mounting carriers inside cover
    esp32_mount_y = -EH/2 + CT + 5
    esp32_carriers = (cq.Workplane("XY")
        .pushPoints([
            (cover_x_start + CT + 10, esp32_mount_y + 1),
            (cover_x_start + CT + 10, esp32_mount_y + c.esp32.length - 1)
        ])
        .rect(7, 2)
        .extrude(c.esp32.mount_height)
        .translate((0, 0, EW/2 - c.esp32.board_width/2)))

    # USB cutout on front face of cover (X = cover_x_end)
    USB_WIDTH = 9.3
    USB_HEIGHT = 3.3
    if c.esp32.usb_height is not None:
        usb_cutout = (cq.Workplane("ZY",
            (cover_x_end,
             esp32_mount_y + c.esp32.length/2,
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
        usb_cutout = dummy

    # Fan mount on top of cover, rear-biased
    fan_x = cover_x_start + CT + c.fan_offset_from_rear + c.fan.size/2
    fan_z = EW / 2

    # Only add fan if it fits within cover dimensions
    if c.fan.size <= CD - 2*CT and c.fan.size <= EW - 2*CT:
        fan_cutout = (cq.Workplane("XY", (fan_x, EH/2, fan_z))
            .rect(c.fan.size, c.fan.size)
            .extrude(-CT - 2))

        fan_screw_cutout = dummy
        hs = c.fan.screw_spacing / 2
        for dx in [-hs, hs]:
            for dz in [-hs, hs]:
                hole = (cq.Workplane("XY", (fan_x + dx, EH/2 + 0.1, fan_z + dz))
                    .circle(c.fan.screw_diam / 2)
                    .extrude(-CT - 2))
                fan_screw_cutout = fan_screw_cutout.union(hole)
    else:
        fan_cutout = dummy
        fan_screw_cutout = dummy

    # Cover ventilation — front face slots
    cover_vents = dummy
    for bi in range(c.num_boards):
        vy = board_y_positions[bi] + sk.pcb_thickness + sk.component_height/2
        vent = (cq.Workplane("XY")
            .box(CT + 2, sk.component_height * 0.4, VENT_WIDTH)
            .translate((cover_x_end, vy, EW/2)))
        cover_vents = cover_vents.union(vent)

    # Wiring opening in cover back wall — lets JST cables pass from base into cover
    wire_opening = (cq.Workplane("XY")
        .box(CT + 2, EH * 0.3, EW * 0.4)
        .translate((cover_x_start + CT/2, 0, EW/2)))

    # ======================== Build COVER ==================

    cover = (cover_outer.cut(cover_inner)
        .cut(comp_channel)
        .union(esp32_carriers)
        .cut(usb_cutout)
        .cut(fan_cutout)
        .cut(fan_screw_cutout)
        .cut(cover_vents)
        .cut(wire_opening)
    )

    # ================================= Export ======================

    results = {
        "base": base,
        "cover": cover,
        "clip": clip,
    }
    if c.NR_WAGO_INTERNAL > 0:
        results["internal_wago_fix"] = internal_wago_fix

    rotations = {
        "base": ((0, 0, 0), (0, 1, 0), 0),
        "cover": ((0, 0, 0), (0, 1, 0), 0),
        "clip": ((0, 0, 0), (0, 1, 0), -90),
        "internal_wago_fix": ((0, 0, 0), (0, 1, 0), 90),
    }

    basename = Path(os.path.basename(__file__)).stem + "_" + c.CONFIG_NAME
    for name in results:
        print(f"{name}: \n {results[name]} \n ")
        rot = rotations.get(name, ((0, 0, 0), (0, 1, 0), 0))
        results[name].rotate(*rot).export(basename + "_" + name + ".stl")

    # Small parts for printing
    clip_r = clip.rotate(*rotations["clip"])
    clip_z = clip_r.val().BoundingBox().zmin
    small_assy = cq.Assembly(clip_r.translate((0, 40, -clip_z)))
    if c.NR_WAGO_INTERNAL > 0:
        wfix_r = internal_wago_fix.rotate(*rotations["internal_wago_fix"])
        wfix_z = wfix_r.val().BoundingBox().zmin
        small_assy = small_assy.add(wfix_r.translate((0, -20, -wfix_z)))
    small_parts = small_assy.toCompound()
    small_parts.export(basename + "_small_parts.stl")

    # STEP assembly
    assembly = cq.Assembly(base).add(cover).add(clip)
    if c.NR_WAGO_INTERNAL > 0:
        assembly = assembly.add(internal_wago_fix)
    assembly.export(basename + "_assembly.step")
    compound = assembly.toCompound()
    compound.export(basename + "_compound.step")

    print(f"Export complete: {basename}")


def show():
    show_object(base)
    show_object(cover)
    for cl in clips:
        show_object(cl)
