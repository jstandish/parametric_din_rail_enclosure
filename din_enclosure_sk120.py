# ==========================================================================================
# SK120 DIN Rail Card-Slot Enclosure Generator
# Bernic High/Low style: two-piece (base + front cover)
#
# Coordinate system:
#   X = depth from DIN rail (0 at rail, positive outward/forward)
#   Y = vertical (0 at center, +Y up, -Y down)
#   Z = width along DIN rail (0 at one edge)
#
# Side profile (XY cross-section) — Bernic High/Low stair-step:
#
#    The LOW section is VERTICALLY CENTERED within the HIGH section.
#    Step appears on BOTH top and bottom at X=STEP_X.
#
#    Y=HIGH_TOP  ────────────────┐
#                                │  HIGH section (BACK, DIN rail)
#    Y=LOW_TOP   ────────────────┤  ← step DOWN (top)
#                ┌───────────────┘
#                │  LOW section (FRONT, centered)
#                └───────────────┐
#    Y=LOW_BOT   ────────────────┤  ← step UP (bottom)
#                                │  HIGH section continues
#    Y=HIGH_BOT  ────────────────┘
#    ══DIN RAIL══
#    X=0(rail)         X=STEP_X   X=TOTAL_DEPTH
#
# HIGH section (back): SK120 boards in card slots, terminal blocks, DIN clip
# LOW section (front):  ESP32 bay + fan, compression-fit cover, centered
# ==========================================================================================

from din_declarations import *

import cadquery as cq
from cadquery.func import *
from pathlib import Path
import os


def generate_enclosure(c: SK120Config):
    EW = c.enclosure_width    # Z (along rail)
    EH = c.enclosure_height   # Y (vertical height of HIGH section)
    CT = c.CASE_THICKNESS
    sk = c.sk120
    CL = c.COMPRESSION_LIP
    CG = c.COMPRESSION_GAP

    # ============ Stair-step profile (Bernic High/Low) ============
    # HIGH section at BACK (DIN rail side): full height, holds boards
    # LOW section at FRONT: vertically CENTERED, shorter, cover fits here

    STEP_X      = sk.pcb_length + 2*CT + c.slot_depth   # board area depth
    LOW_DEPTH   = c.COVER_DEPTH                          # front section depth
    TOTAL_DEPTH = STEP_X + LOW_DEPTH

    # HIGH section vertical extent (full height)
    HIGH_TOP_Y = EH / 2
    HIGH_BOT_Y = -EH / 2

    # LOW section is centered vertically, with STEP_HEIGHT ledge on each side
    STEP_HEIGHT = 10.0   # step on each side (top and bottom)
    LOW_TOP_Y   = HIGH_TOP_Y - STEP_HEIGHT
    LOW_BOT_Y   = HIGH_BOT_Y + STEP_HEIGHT
    LOW_HEIGHT  = LOW_TOP_Y - LOW_BOT_Y

    # LOW section has 3 compartments (bottom to top):
    #   Bottom: input terminal block (2-port)
    #   Middle: ESP32 electronics bay
    #   Top:    output terminal block (6-port)
    TERM_COMP_HEIGHT = 12.0   # height of each terminal compartment
    LOW_INNER = LOW_HEIGHT - 2*CT
    ESP32_COMP_HEIGHT = LOW_INNER - 2*TERM_COMP_HEIGHT - 2*CT  # middle gets remainder

    # Compartment Y boundaries (inside LOW section)
    COMP_BOT_BOT  = LOW_BOT_Y + CT                               # bottom comp floor
    COMP_BOT_TOP  = COMP_BOT_BOT + TERM_COMP_HEIGHT              # bottom comp ceiling
    DIVIDER_BOT_Y = COMP_BOT_TOP                                  # bottom divider starts
    COMP_MID_BOT  = DIVIDER_BOT_Y + CT                            # middle comp floor
    COMP_MID_TOP  = COMP_MID_BOT + ESP32_COMP_HEIGHT              # middle comp ceiling
    DIVIDER_TOP_Y = COMP_MID_TOP                                   # top divider starts
    COMP_TOP_BOT  = DIVIDER_TOP_Y + CT                             # top comp floor
    COMP_TOP_TOP  = LOW_TOP_Y - CT                                 # top comp ceiling

    BACK_WALL_X = -5

    # Board area in HIGH section
    BOARD_AREA_X_START = CT
    BOARD_AREA_X_END   = STEP_X - CT

    print(f"Generating SK120 enclosure: {c.CONFIG_NAME}")
    print(f"  Width (Z):            {EW}mm")
    print(f"  HIGH depth (X):       {STEP_X}mm (back/DIN rail)")
    print(f"  LOW depth (X):        {LOW_DEPTH}mm (front/cover)")
    print(f"  Total depth (X):      {TOTAL_DEPTH}mm")
    print(f"  HIGH height (Y):      {EH}mm  ({HIGH_BOT_Y:.1f} to {HIGH_TOP_Y:.1f})")
    print(f"  LOW height (Y):       {LOW_HEIGHT:.1f}mm  ({LOW_BOT_Y:.1f} to {LOW_TOP_Y:.1f})")
    print(f"  Step (each side):     {STEP_HEIGHT}mm")
    print(f"  LOW compartments:     bot={TERM_COMP_HEIGHT}mm, mid={ESP32_COMP_HEIGHT:.1f}mm, top={TERM_COMP_HEIGHT}mm")
    print(cq.__version__)

    global base, cover, clips

    # Board slot pitch
    board_layer_height = sk.component_height + sk.pcb_thickness + c.board_spacing

    # Y positions of each board's PCB bottom
    board_y_positions = []
    for i in range(c.num_boards):
        y_bottom = HIGH_BOT_Y + CT + c.board_spacing + i * board_layer_height
        board_y_positions.append(y_bottom)

    # ======================== dummy object ==================
    dummy = cq.Workplane("XY").box(0.1, 0.1, 0.1).translate((-0.1, HIGH_TOP_Y - 10, 5))

    # ======================== DIN rail clip ==================
    # Behind HIGH section back wall — same as original din_enclosure.py

    CLIP_WIDTH         = EW - 2*CT - 0.2
    CLIP_GAP           = 0.1
    CLIP_THICKNESS     = 3.5
    CLIP_SLOT_DEPTH    = CLIP_THICKNESS
    CLIP_HIDDEN_LENGTH = EH/2 - c.DIN_RAIL_LOWER + CLIP_SLOT_DEPTH
    CLIP_TOP_HEIGHT    = 8
    CLIP_LEG_WIDTH     = 2.6
    CLIP_LEG_HEADROOM  = 1
    CLIP_LEG_RADIUS    = 1.2
    CLIP_LEG_LENGTH    = CLIP_HIDDEN_LENGTH - CLIP_TOP_HEIGHT - CLIP_LEG_HEADROOM
    CLIP_LEG_GAP_WIDTH = 1.5
    CLIP_BASE_HEIGHT   = 6
    CLIP_CHAMFER       = 1.5
    CLIP_UPPER_LOCK    = CLIP_TOP_HEIGHT - CLIP_SLOT_DEPTH + CLIP_LEG_HEADROOM + CLIP_LEG_RADIUS
    CLIP_LOCK_DISTANCE = 5
    CLIP_SLOT_WIDTH    = 1.4
    CLIP_SLOT_TAPER    = 3
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
        .translate((-(CLIP_THICKNESS + CLIP_GAP), HIGH_BOT_Y, clip_z))
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

    # ======================== WAGO fixation ==================

    WAGO_FIX_HEIGHT  = 2.5
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
        wago_221_fix    = wago_221_fix.rotate((0, 0, 0), (0, 1, 0), -90).translate((x, y, z))
        wago_fix_cutout = wago_fix_cutout.rotate((0, 0, 0), (0, 1, 0), -90).translate((x, y, z))
        return wago_221_fix, wago_fix_cutout

    wago_x = CT + c.WAGO_HEIGHT + WAGO_FIX_HEIGHT/2
    wago_y = HIGH_BOT_Y + CT + c.WAGO_FIX_WIDTH/2 + 1
    wago_z = EW / 2

    if c.NR_WAGO_INTERNAL > 0:
        internal_wago_fix, internal_wago_fix_cutout = wago_fix(
            c.NR_WAGO_INTERNAL, wago_x, wago_y, wago_z)
    else:
        internal_wago_fix        = dummy
        internal_wago_fix_cutout = dummy

    # ================================================================
    #                         BASE PART
    # Bernic High/Low: HIGH back + centered LOW front
    # Step on BOTH top and bottom at X=STEP_X
    # ================================================================

    base_sketch_outer = (cq.Sketch()
        # Start at upper DIN rail notch
        .segment((0, c.DIN_RAIL_UPPER), (-0.8, c.DIN_RAIL_UPPER))
        .segment((-3.2, c.DIN_RAIL_UPPER - 3.2))
        .segment((BACK_WALL_X, c.DIN_RAIL_UPPER - 3.2))
        # Up back wall to HIGH_TOP
        .segment((BACK_WALL_X, HIGH_TOP_Y))
        # Across HIGH top to step
        .segment((STEP_X, HIGH_TOP_Y))
        # Step DOWN on top to LOW_TOP
        .segment((STEP_X, LOW_TOP_Y))
        # Across LOW top to front
        .segment((TOTAL_DEPTH, LOW_TOP_Y))
        # Down front wall (LOW section height only)
        .segment((TOTAL_DEPTH, LOW_BOT_Y))
        # Step UP on bottom to HIGH_BOT (back to full height)
        .segment((STEP_X, LOW_BOT_Y))
        .segment((STEP_X, HIGH_BOT_Y))
        # Across HIGH bottom to back wall
        .segment((BACK_WALL_X, HIGH_BOT_Y))
        # Up back wall to lower DIN rail notch
        .segment((BACK_WALL_X, -c.DIN_RAIL_LOWER))
        .segment((0, -c.DIN_RAIL_LOWER))
        .close()
        .assemble(tag="outerface")
        .vertices()
        .fillet(0.5)
        .clean()
    )

    # Inner cavity — follows the centered step
    base_sketch_inner = (cq.Sketch()
        .segment((CT, HIGH_BOT_Y + CT), (CT, HIGH_TOP_Y - CT))       # back inside
        .segment((STEP_X - CT, HIGH_TOP_Y - CT))                      # HIGH ceiling
        .segment((STEP_X - CT, LOW_TOP_Y - CT))                       # step down (top)
        .segment((TOTAL_DEPTH - CT, LOW_TOP_Y - CT))                   # LOW ceiling
        .segment((TOTAL_DEPTH - CT, LOW_BOT_Y + CT))                   # front inside
        .segment((STEP_X - CT, LOW_BOT_Y + CT))                       # step up (bottom)
        .segment((STEP_X - CT, HIGH_BOT_Y + CT))                      # HIGH floor
        .close()
        .assemble(tag="innerface")
        .vertices()
        .fillet(0.6)
        .clean()
    )

    base_outer = cq.Workplane("XY").placeSketch(base_sketch_outer).extrude(EW)
    base_inner = cq.Workplane("XY", (0, 0, EW)).placeSketch(base_sketch_inner).extrude(-(EW - CT))

    # ======================== Card slot shelves and grooves ==================
    # Boards in HIGH (back) section

    slot_w          = sk.pcb_thickness + sk.slot_clearance
    board_area_depth = BOARD_AREA_X_END - BOARD_AREA_X_START

    shelves = dummy
    for i in range(c.num_boards + 1):
        if i == 0:
            shelf_y = board_y_positions[0] - c.board_spacing / 2
        elif i == c.num_boards:
            shelf_y = board_y_positions[-1] + sk.pcb_thickness + sk.component_height + c.board_spacing / 2
        else:
            shelf_y = (board_y_positions[i-1] + sk.pcb_thickness + sk.component_height
                       + board_y_positions[i]) / 2

        shelf = (cq.Workplane("XY")
            .box(board_area_depth, c.board_spacing, EW - 2*CT)
            .translate((BOARD_AREA_X_START + board_area_depth/2, shelf_y, EW/2)))
        shelves = shelves.union(shelf)

    slot_cutouts = dummy
    for i in range(c.num_boards):
        pcb_y = board_y_positions[i] + sk.pcb_thickness / 2
        left_groove = (cq.Workplane("XY")
            .box(board_area_depth, slot_w, c.slot_depth)
            .translate((BOARD_AREA_X_START + board_area_depth/2, pcb_y, CT + c.slot_depth/2)))
        right_groove = (cq.Workplane("XY")
            .box(board_area_depth, slot_w, c.slot_depth)
            .translate((BOARD_AREA_X_START + board_area_depth/2, pcb_y, EW - CT - c.slot_depth/2)))
        slot_cutouts = slot_cutouts.union(left_groove).union(right_groove)

    # ======================== LOW section divider walls ==================
    # Two horizontal walls separating the 3 compartments in the LOW section
    # Span from step wall (STEP_X) to front wall (TOTAL_DEPTH-CT), full width

    low_divider_depth = TOTAL_DEPTH - STEP_X - CT   # X span inside LOW section
    low_divider_x     = STEP_X + low_divider_depth/2 + CT/2

    divider_bottom = (cq.Workplane("XY")
        .box(low_divider_depth, CT, EW - 2*CT)
        .translate((low_divider_x, DIVIDER_BOT_Y + CT/2, EW/2)))

    divider_top = (cq.Workplane("XY")
        .box(low_divider_depth, CT, EW - 2*CT)
        .translate((low_divider_x, DIVIDER_TOP_Y + CT/2, EW/2)))

    # ======================== Wire pass-through channels ==================
    # Rectangular openings in the step wall at X=STEP_X connecting HIGH → each LOW compartment
    PASSTHROUGH_W = 20.0    # Z width of channel
    PASSTHROUGH_H = 8.0     # Y height of channel

    wire_passthrough = dummy
    for comp_bot, comp_top in [(COMP_BOT_BOT, COMP_BOT_TOP),
                                (COMP_MID_BOT, COMP_MID_TOP),
                                (COMP_TOP_BOT, COMP_TOP_TOP)]:
        comp_center_y = (comp_bot + comp_top) / 2
        ch = (cq.Workplane("XY")
            .box(CT + 2, PASSTHROUGH_H, PASSTHROUGH_W)
            .translate((STEP_X, comp_center_y, EW/2)))
        wire_passthrough = wire_passthrough.union(ch)

    # ======================== Wire gutters in HIGH section ==================
    # Shallow channels along the left side wall of the HIGH section,
    # routing wires from each step-wall pass-through back into the board area.
    GUTTER_DEPTH  = 3.0    # carved into side wall (Z direction)
    GUTTER_WIDTH  = 8.0    # Y direction
    GUTTER_LENGTH = STEP_X - CT - 10  # X direction, from near step wall back into board area

    wire_gutters = dummy
    for comp_bot, comp_top in [(COMP_BOT_BOT, COMP_BOT_TOP),
                                (COMP_MID_BOT, COMP_MID_TOP),
                                (COMP_TOP_BOT, COMP_TOP_TOP)]:
        comp_center_y = (comp_bot + comp_top) / 2
        # Left side gutter
        gutter = (cq.Workplane("XY")
            .box(GUTTER_LENGTH, GUTTER_WIDTH, GUTTER_DEPTH)
            .translate((STEP_X - GUTTER_LENGTH/2, comp_center_y, CT + GUTTER_DEPTH/2)))
        wire_gutters = wire_gutters.union(gutter)

    # ======================== Side ventilation (HIGH section) ==================

    VENT_WIDTH   = 2.0
    VENT_SPACING = 4.0
    base_vents   = dummy

    vent_x_start = BOARD_AREA_X_START + 5
    vent_x_end   = BOARD_AREA_X_END - 5
    num_vents = max(0, int((vent_x_end - vent_x_start) / (VENT_WIDTH + VENT_SPACING)))
    for vi in range(num_vents):
        vx = vent_x_start + vi * (VENT_WIDTH + VENT_SPACING) + VENT_WIDTH/2
        for bi in range(c.num_boards):
            vy = board_y_positions[bi] + sk.pcb_thickness + sk.component_height/2
            vent_l = (cq.Workplane("XY")
                .box(VENT_WIDTH, sk.component_height * 0.5, CT + 2)
                .translate((vx, vy, 0)))
            vent_r = (cq.Workplane("XY")
                .box(VENT_WIDTH, sk.component_height * 0.5, CT + 2)
                .translate((vx, vy, EW)))
            base_vents = base_vents.union(vent_l).union(vent_r)

    # ======================== Terminal block cutouts on base front face ==================
    # Cut through the base front wall at X=TOTAL_DEPTH for screw terminal access

    # Bottom compartment: 2-port input terminal
    pi = c.power_input
    input_term_y = (COMP_BOT_BOT + COMP_BOT_TOP) / 2
    input_terminal_cutout = (cq.Workplane("XY")
        .box(CT + 2, pi.height + 1, pi.width + 1)
        .translate((TOTAL_DEPTH, input_term_y, EW/2)))

    # Top compartment: 6-port output terminal
    po = c.power_output
    output_term_y = (COMP_TOP_BOT + COMP_TOP_TOP) / 2
    output_terminal_cutout = (cq.Workplane("XY")
        .box(CT + 2, po.height + 1, po.width + 1)
        .translate((TOTAL_DEPTH, output_term_y, EW/2)))

    # ======================== ESP32 mounting in base middle compartment ==================
    esp32_mount_y = COMP_MID_BOT + 2
    esp32_carriers = (cq.Workplane("XY")
        .pushPoints([
            (STEP_X + CT + 5, esp32_mount_y + 1),
            (STEP_X + CT + 5, esp32_mount_y + c.esp32.length - 1)
        ])
        .rect(7, 2)
        .extrude(c.esp32.mount_height)
        .translate((0, 0, EW/2 - c.esp32.board_width/2)))

    # USB cutout on base front face (middle compartment)
    USB_W = 9.3
    USB_H = 3.3
    if c.esp32.usb_height is not None:
        usb_cutout = (cq.Workplane("ZY",
            (TOTAL_DEPTH,
             esp32_mount_y + c.esp32.length/2,
             EW/2))
            .moveTo(0, USB_H/2)
            .hLine(USB_W/2 - USB_H/2)
            .threePointArc((USB_W/2, 0), (USB_W/2 - USB_H/2, -USB_H/2))
            .hLine(-USB_W + USB_H)
            .threePointArc((-USB_W/2, 0), (-USB_W/2 + USB_H/2, USB_H/2))
            .hLine(USB_W/2 - USB_H/2)
            .close()
            .extrude(-CT - 1, taper=-30))
    else:
        usb_cutout = dummy

    # ======================== Fan cutout on base LOW section top ==================
    fan_x = STEP_X + CT + c.fan_offset_from_rear + c.fan.size/2
    fan_z = EW / 2
    low_section_x_span = TOTAL_DEPTH - STEP_X - 2*CT

    can_fit_fan = (c.fan.size <= low_section_x_span and c.fan.size <= EW - 2*CT)
    if can_fit_fan:
        fan_cutout = (cq.Workplane("XY", (fan_x, LOW_TOP_Y, fan_z))
            .rect(c.fan.size, c.fan.size)
            .extrude(-CT - 2))
        fan_screw_cutout = dummy
        hs = c.fan.screw_spacing / 2
        for dx in [-hs, hs]:
            for dz in [-hs, hs]:
                hole = (cq.Workplane("XY", (fan_x + dx, LOW_TOP_Y + 0.1, fan_z + dz))
                    .circle(c.fan.screw_diam / 2)
                    .extrude(-CT - 2))
                fan_screw_cutout = fan_screw_cutout.union(hole)
    else:
        fan_cutout       = dummy
        fan_screw_cutout = dummy

    # ======================== Cover screw inserts in base front wall ==================
    COVER_SCREW_DIAM = 3.0
    cover_screw_y_positions = [LOW_BOT_Y + CT + 3, LOW_TOP_Y - CT - 3]
    base_screw_inserts = dummy
    for sy in cover_screw_y_positions:
        hole = (cq.Workplane("XY", (TOTAL_DEPTH + 0.1, sy, EW/2))
            .circle(c.SCREW_INSERT_DIAM / 2)
            .extrude(-c.SCREW_INSERT_DEPTH))
        base_screw_inserts = base_screw_inserts.union(hole)

    # ======================== Text ==================

    text_brand = (cq.Workplane("YZ", (BACK_WALL_X, 0, EW/2))
        .text(c.BRAND, 5, -0.3))
    if c.MODULE_NAME:
        text_name = (cq.Workplane("XZ", (STEP_X/2, HIGH_TOP_Y, EW/2))
            .text(c.MODULE_NAME, 5, -0.3))
    else:
        text_name = dummy

    # ======================== Build BASE ==================

    base = (base_outer.cut(base_inner)
        .cut(clip_cutout)
        .union(shelves)
        .cut(slot_cutouts)
        .union(divider_bottom)
        .union(divider_top)
        .cut(wire_passthrough)
        .cut(wire_gutters)
        .union(esp32_carriers)
        .cut(usb_cutout)
        .cut(input_terminal_cutout)
        .cut(output_terminal_cutout)
        .cut(fan_cutout)
        .cut(fan_screw_cutout)
        .union(internal_wago_fix)
        .cut(internal_wago_fix_cutout)
        .cut(base_vents)
        .cut(text_brand)
        .cut(text_name)
        .cut(base_screw_inserts)
    )

    # ================================================================
    #                       FRONT COVER (flat plate)
    # Simple flat plate covering the open LOW section front face.
    # Attaches at X=TOTAL_DEPTH, spans LOW_BOT_Y to LOW_TOP_Y + margins.
    # All terminal cutouts, ESP32, fan are on the base part.
    # ================================================================

    cover_height = LOW_TOP_Y - LOW_BOT_Y + 2*CT  # covers full LOW opening with overlap
    cover = (cq.Workplane("XY")
        .box(CT, cover_height, EW)
        .translate((TOTAL_DEPTH + CT/2, (LOW_TOP_Y + LOW_BOT_Y)/2, EW/2)))

    # Matching terminal cutouts on cover plate (for terminal access)
    cover_input_cutout = (cq.Workplane("XY")
        .box(CT + 2, pi.height + 1, pi.width + 1)
        .translate((TOTAL_DEPTH + CT/2, input_term_y, EW/2)))
    cover_output_cutout = (cq.Workplane("XY")
        .box(CT + 2, po.height + 1, po.width + 1)
        .translate((TOTAL_DEPTH + CT/2, output_term_y, EW/2)))

    # Matching USB cutout on cover plate
    if c.esp32.usb_height is not None:
        cover_usb_cutout = (cq.Workplane("ZY",
            (TOTAL_DEPTH + CT + 0.1,
             esp32_mount_y + c.esp32.length/2,
             EW/2))
            .moveTo(0, USB_H/2)
            .hLine(USB_W/2 - USB_H/2)
            .threePointArc((USB_W/2, 0), (USB_W/2 - USB_H/2, -USB_H/2))
            .hLine(-USB_W + USB_H)
            .threePointArc((-USB_W/2, 0), (-USB_W/2 + USB_H/2, USB_H/2))
            .hLine(USB_W/2 - USB_H/2)
            .close()
            .extrude(-CT - 1))
    else:
        cover_usb_cutout = dummy

    # Cover screw holes (pass-through for screws into base inserts)
    cover_screw_holes = dummy
    for sy in cover_screw_y_positions:
        hole = (cq.Workplane("XY", (TOTAL_DEPTH + CT + 0.1, sy, EW/2))
            .circle(COVER_SCREW_DIAM / 2)
            .extrude(-CT - 2))
        cover_screw_holes = cover_screw_holes.union(hole)

    # ======================== Build COVER ==================

    cover = (cover
        .cut(cover_input_cutout)
        .cut(cover_output_cutout)
        .cut(cover_usb_cutout)
        .cut(cover_screw_holes)
    )

    # ================================= Export ======================

    results = {
        "base":  base,
        "cover": cover,
        "clip":  clip,
    }
    if c.NR_WAGO_INTERNAL > 0:
        results["internal_wago_fix"] = internal_wago_fix

    rotations = {
        "base":              ((0, 0, 0), (0, 1, 0),  0),
        "cover":             ((0, 0, 0), (0, 1, 0),  0),
        "clip":              ((0, 0, 0), (0, 1, 0), -90),
        "internal_wago_fix": ((0, 0, 0), (0, 1, 0),  90),
    }

    basename = Path(os.path.basename(__file__)).stem + "_" + c.CONFIG_NAME
    for name in results:
        rot = rotations.get(name, ((0, 0, 0), (0, 1, 0), 0))
        results[name].rotate(*rot).export(basename + "_" + name + ".stl")
        print(f"  Exported {name}")

    # Small parts plate
    clip_r     = clip.rotate(*rotations["clip"])
    clip_z_min = clip_r.val().BoundingBox().zmin
    small_assy = cq.Assembly(clip_r.translate((0, 40, -clip_z_min)))
    if c.NR_WAGO_INTERNAL > 0:
        wfix_r     = internal_wago_fix.rotate(*rotations["internal_wago_fix"])
        wfix_z_min = wfix_r.val().BoundingBox().zmin
        small_assy = small_assy.add(wfix_r.translate((0, -20, -wfix_z_min)))
    small_assy.toCompound().export(basename + "_small_parts.stl")

    # STEP assembly
    assembly = cq.Assembly(base).add(cover).add(clip)
    if c.NR_WAGO_INTERNAL > 0:
        assembly = assembly.add(internal_wago_fix)
    assembly.export(basename + "_assembly.step")
    assembly.toCompound().export(basename + "_compound.step")

    print(f"Export complete: {basename}")


def show():
    show_object(base)
    show_object(cover)
    for cl in clips:
        show_object(cl)
