# SK120 DIN Rail Card-Slot Enclosure Generator
# Generates enclosure for 3 headless XY-SK120X DC-DC converters
# with ESP32 bay, parametric fan, and power distribution

from din_declarations import *
import cadquery as cq
from pathlib import Path
import os


def generate_enclosure(c: SK120Config):
    print(f"Generating SK120 enclosure: {c.CONFIG_NAME}")
    print(f"  Enclosure width: {c.enclosure_width}mm")
    print(f"  Enclosure depth: {c.enclosure_depth}mm")
    print(f"  DIN height: {c.DIN_HEIGHT}mm")

    global case, lid, clips

    EW = c.enclosure_width   # total width along DIN rail (Z axis)
    ED = c.enclosure_depth   # total depth from rail (X axis)
    EH = c.DIN_HEIGHT        # height (Y axis)
    CT = c.CASE_THICKNESS
    sk = c.sk120

    # card slot zone width (Z) — just the SK120 section
    card_zone_width = c.num_boards * sk.pcb_width + (c.num_boards + 1) * c.board_spacing

    # dummy cutout for optional features
    dummy = cq.Workplane("XY").box(0.1, 0.1, 0.1).translate((-0.1, EH/2 - 10, 5))

    # ======================== DIN rail clips ===================================
    # Generate multiple clips spaced along the wide enclosure

    CLIP_UNIT_WIDTH = 14.0  # standard clip width
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
        """Generate a single DIN rail clip centered at z_pos along the Z axis."""
        cl = (cq.Workplane("front")
            .moveTo(0, -CLIP_BASE_HEIGHT)
            .hLine(CLIP_UNIT_WIDTH/2.0)
            .vLine(CLIP_LEG_LENGTH + CLIP_BASE_HEIGHT - 2*CLIP_LEG_RADIUS)
            .threePointArc((CLIP_UNIT_WIDTH/2 + CLIP_LEG_RADIUS, CLIP_LEG_LENGTH - CLIP_LEG_RADIUS),
                           (CLIP_UNIT_WIDTH/2, CLIP_LEG_LENGTH))
            .hLine(-CLIP_LEG_WIDTH)
            .vLine(-CLIP_LEG_LENGTH)
            .hLine(-CLIP_LEG_GAP_WIDTH)
            .vLine(CLIP_HIDDEN_LENGTH - CLIP_TOP_HEIGHT)
            .hLine(CLIP_LEG_GAP_WIDTH + CLIP_LEG_WIDTH)
            .vLine(CLIP_TOP_HEIGHT)
            .hLine(-CLIP_UNIT_WIDTH/2)
            .mirrorY()
            .moveTo(0, -3)
            .rect(6, 2)
            .extrude(CLIP_THICKNESS)
            .edges(">(0, 1, -1)").chamfer(CLIP_CHAMFER)
            .edges("|Z").fillet(0.5)
            .faces(">Y").workplane()
            .center(0, (CLIP_THICKNESS - CLIP_SLOT_WIDTH/2 + 0.18))
            .rect(CLIP_UNIT_WIDTH + 3, CLIP_SLOT_WIDTH)
            .extrude(-CLIP_SLOT_DEPTH, combine='s', taper=CLIP_SLOT_TAPER)
            .rotate((0, 0, 0), (0, 1, 0), 90)
            .translate((-(CLIP_THICKNESS + CLIP_GAP), -EH/2, z_pos))
        )
        return cl

    def make_clip_cutout(z_pos):
        """Generate clip cutout at z_pos."""
        cc = cq.Workplane("XY").box(CLIP_THICKNESS + 2*CLIP_GAP, CLIP_CUTOUT_HEIGHT,
                                     CLIP_UNIT_WIDTH + 2*CLIP_GAP)
        cc = (cc.faces("<X").workplane()
            .center(-CLIP_CUTOUT_HEIGHT/2 + CLIP_UPPER_LOCK, -CLIP_UNIT_WIDTH/2)
            .circle(CLIP_LEG_RADIUS + CLIP_GAP)
            .center(0, CLIP_UNIT_WIDTH)
            .circle(CLIP_LEG_RADIUS + CLIP_GAP)
            .center(CLIP_LOCK_DISTANCE, 0)
            .circle(CLIP_LEG_RADIUS + CLIP_GAP)
            .center(0, -CLIP_UNIT_WIDTH)
            .circle(CLIP_LEG_RADIUS + CLIP_GAP)
            .extrude(-CLIP_THICKNESS - 2*CLIP_GAP)
        )
        cc = cc.translate((-CLIP_THICKNESS/2 - CLIP_GAP,
                           -CLIP_CUTOUT_HEIGHT/2 - c.DIN_RAIL_LOWER,
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

    # ====================== main case body =========================

    # Simplified DIN rail profile (XY cross-section, extruded along Z)
    # Back wall has DIN rail notches, rest is rectangular
    sketch_outer = (cq.Sketch()
        # Start at bottom-back, go clockwise
        .segment((0, -c.DIN_RAIL_LOWER), (-0.8, -c.DIN_RAIL_LOWER))   # bottom rail notch
        .segment((-3.2, -c.DIN_RAIL_LOWER + 3.2))
        .segment((-5, -c.DIN_RAIL_LOWER + 3.2))
        .segment((-5, -EH/2))                                          # bottom-back corner
        .segment((ED, -EH/2))                                          # bottom-front corner
        .segment((ED, EH/2))                                           # top-front corner
        .segment((-5, EH/2))                                           # top-back corner
        .segment((-5, c.DIN_RAIL_UPPER - 3.2))
        .segment((-3.2, c.DIN_RAIL_UPPER - 3.2))                      # top rail notch
        .segment((-0.8, c.DIN_RAIL_UPPER))
        .segment((0, c.DIN_RAIL_UPPER))
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

    # ====================== card slot dividers =========================

    # Each divider is a wall running front-to-back with grooves for PCB edges
    dividers = dummy
    slot_w = sk.pcb_thickness + sk.slot_clearance  # groove width
    divider_depth = ED - 2 * CT  # how deep dividers run (X)
    divider_height = EH - 2 * CT  # full internal height (Y)

    for i in range(c.num_boards + 1):
        # Z position of divider center
        z_pos = CT + i * (sk.pcb_width + c.board_spacing) + c.board_spacing / 2
        divider = (cq.Workplane("XY")
            .box(divider_depth, divider_height, c.board_spacing)
            .translate((CT + divider_depth/2, 0, z_pos))
        )
        dividers = dividers.union(divider)

    # Create grooves (cutouts) in the dividers for PCB edges
    slot_cutouts = dummy
    for i in range(c.num_boards):
        # Each board sits between divider i and divider i+1
        # Left groove (in right face of divider i)
        z_left = CT + i * (sk.pcb_width + c.board_spacing) + c.board_spacing
        left_groove = (cq.Workplane("XY")
            .box(divider_depth, divider_height, slot_w)
            .translate((CT + divider_depth/2, 0, z_left - slot_w/2 + c.slot_depth))
        )
        # Actually, the groove should be a channel cut into the divider face
        # Groove on right side of left divider
        left_groove = (cq.Workplane("XY")
            .box(c.slot_depth, divider_height, slot_w)
            .translate((CT + divider_depth/2, 0,
                        z_left + slot_w/2))
        )
        # Groove on left side of right divider
        z_right = CT + (i + 1) * (sk.pcb_width + c.board_spacing) + c.board_spacing/2
        right_groove_z = z_right - c.board_spacing/2
        right_groove = (cq.Workplane("XY")
            .box(c.slot_depth, divider_height, slot_w)
            .translate((CT + divider_depth/2, 0,
                        right_groove_z - slot_w/2))
        )
        slot_cutouts = slot_cutouts.union(left_groove).union(right_groove)

    # Bottom shelf/stop for each board (small ledge)
    shelves = dummy
    shelf_height = CT  # thickness of the shelf
    for i in range(c.num_boards):
        z_center = CT + c.board_spacing + i * (sk.pcb_width + c.board_spacing) + sk.pcb_width/2
        shelf = (cq.Workplane("XY")
            .box(divider_depth, shelf_height, sk.pcb_width)
            .translate((CT + divider_depth/2,
                        -EH/2 + CT + shelf_height/2,
                        z_center))
        )
        shelves = shelves.union(shelf)

    # ====================== ESP32 bay =========================

    # ESP32 bay is at the high-Z end of the enclosure
    esp32_z_start = CT + card_zone_width
    esp32_z_center = esp32_z_start + c.esp32_section_width / 2

    # Divider wall between card slots and ESP32 bay (already created as last divider above)
    # Wiring opening in the divider for JST cables
    wire_opening = (cq.Workplane("XY")
        .box(20, 15, c.board_spacing + 2)
        .translate((CT + divider_depth/2, 0,
                    CT + c.num_boards * (sk.pcb_width + c.board_spacing) + c.board_spacing/2))
    )

    # ESP32 mounting carriers (support blocks)
    esp32_carrier_h = c.esp32.mount_height
    esp32_carriers = (cq.Workplane("XY")
        .box(7, 2, c.esp32.board_width)
        .translate((CT + c.esp32.board_width/2 + 5,
                    -EH/2 + CT + esp32_carrier_h/2 + 1,
                    esp32_z_center))
    )

    # USB cutout for ESP32 (on top face)
    USB_WIDTH = 9.3
    USB_HEIGHT = 3.3
    usb_cutout = (cq.Workplane("XZ", (CT + c.esp32.board_width/2 + 5,
                                       EH/2,
                                       esp32_z_center))
        .moveTo(0, USB_HEIGHT/2)
        .hLine(USB_WIDTH/2 - USB_HEIGHT/2)
        .threePointArc((USB_WIDTH/2, 0), (USB_WIDTH/2 - USB_HEIGHT/2, -USB_HEIGHT/2))
        .hLine(-USB_WIDTH + USB_HEIGHT)
        .threePointArc((-USB_WIDTH/2, 0), (-USB_WIDTH/2 + USB_HEIGHT/2, USB_HEIGHT/2))
        .hLine(USB_WIDTH/2 - USB_HEIGHT/2)
        .close()
        .extrude(CT + 1, taper=-30)
    )

    # ====================== power input (bottom) =========================

    # 2-pole screw terminal cutout on bottom face, centered on card slot zone
    pi = c.power_input
    power_in_z = CT + card_zone_width / 2
    power_in_cutout = (cq.Workplane("XY")
        .box(pi.depth + 2, CT + 2, pi.width + 1)
        .translate((CT + pi.depth/2 + 5,
                    -EH/2,
                    power_in_z))
    )

    # ====================== power output (top) =========================

    # One 2-pole screw terminal cutout per board on top face
    po = c.power_output
    power_out_cutouts = dummy
    for i in range(c.num_boards):
        z_center = CT + c.board_spacing + i * (sk.pcb_width + c.board_spacing) + sk.pcb_width/2
        cutout = (cq.Workplane("XY")
            .box(po.depth + 2, CT + 2, po.width + 1)
            .translate((CT + po.depth/2 + 5,
                        EH/2,
                        z_center))
        )
        power_out_cutouts = power_out_cutouts.union(cutout)

    # ====================== internal WAGO mounts =========================

    WAGO_FIX_HEIGHT = 2.5
    WAGO_FIX_EXTRUDE = 1.25

    # Position WAGOs between power input and card slots, near bottom
    wago_x = CT + 5
    wago_y = -EH/2 + CT + 10
    wago_z_vplus = power_in_z - 12
    wago_z_vminus = power_in_z + 12

    # WAGO holder blocks
    wago_holder_vplus = (cq.Workplane("XY")
        .box(c.WAGO_FIX_WIDTH, WAGO_FIX_HEIGHT, 10)
        .translate((wago_x, wago_y, wago_z_vplus))
    )
    wago_holder_vminus = (cq.Workplane("XY")
        .box(c.WAGO_FIX_WIDTH, WAGO_FIX_HEIGHT, 10)
        .translate((wago_x, wago_y, wago_z_vminus))
    )
    wago_holders = wago_holder_vplus.union(wago_holder_vminus)

    # ====================== fan mount (lid, rear-biased) =========================

    fan_x = CT + c.fan_offset_from_rear + c.fan.size/2  # biased toward rear
    fan_z = CT + card_zone_width / 2  # centered on card slot zone

    fan_cutout = (cq.Workplane("XY", (fan_x, EH/2, fan_z))
        .rect(c.fan.size, c.fan.size)
        .extrude(-CT - 2)
    )

    # Fan screw holes
    fan_screw_cutout = dummy
    half_spacing = c.fan.screw_spacing / 2
    for dx in [-half_spacing, half_spacing]:
        for dz in [-half_spacing, half_spacing]:
            hole = (cq.Workplane("XY", (fan_x + dx, EH/2, fan_z + dz))
                .circle(c.fan.screw_diam / 2)
                .extrude(-CT - 2)
            )
            fan_screw_cutout = fan_screw_cutout.union(hole)

    # ====================== ventilation slots =========================

    # Front face ventilation (X = ED)
    vent_slots = dummy
    vent_width = 2.0
    vent_height = 20.0
    vent_spacing = 5.0
    num_vents = int(card_zone_width / vent_spacing) - 1

    for i in range(num_vents):
        z_pos = CT + vent_spacing + i * vent_spacing
        if z_pos + vent_width/2 < CT + card_zone_width:
            slot = (cq.Workplane("XY")
                .box(CT + 2, vent_height, vent_width)
                .translate((ED, 0, z_pos))
            )
            vent_slots = vent_slots.union(slot)

    # ====================== screw blocks =========================

    def case_screw_block(x, y, z):
        sz = c.SCREW_BLOCK_SIZE
        return (cq.Workplane("XY")
            .box(sz, sz, sz)
            .faces(">Z").cboreHole(c.SCREW_HOLE_DIAM, c.SCREW_INSERT_DIAM,
                                    c.SCREW_INSERT_DEPTH, c.SCREW_HOLE_DEPTH)
            .translate((x, y, z))
            .edges("|Z").fillet(1)
        )

    def lid_screw_block(x, y, z):
        sz = c.SCREW_BLOCK_SIZE
        return (cq.Workplane("XY")
            .box(sz, sz, CT + c.SCREW_LID_EXTRA)
            .translate((x, y, z))
            .edges("|Z").fillet(1)
        )

    # 4 screw positions at corners of the enclosure
    screw_margin = c.SCREW_BLOCK_SIZE/2 + CT + 2
    screw_positions = [
        (screw_margin, EH/2 - screw_margin, CT + screw_margin),
        (screw_margin, -EH/2 + screw_margin, CT + screw_margin),
        (screw_margin, EH/2 - screw_margin, EW - screw_margin),
        (screw_margin, -EH/2 + screw_margin, EW - screw_margin),
    ]
    # Add middle screws for wide enclosure
    screw_positions.append((screw_margin, EH/2 - screw_margin, EW/2))
    screw_positions.append((screw_margin, -EH/2 + screw_margin, EW/2))

    case_screw_blocks = []
    lid_screw_blocks = []
    for (x, y, z) in screw_positions:
        case_screw_blocks.append(case_screw_block(x, y, z))
        lid_screw_blocks.append(lid_screw_block(x, y, z))

    # ====================== text / branding =========================

    text_brand = cq.Workplane("YX").center(0, 12).text(c.BRAND, 8, -0.3)
    if c.MODULE_NAME:
        text_name = (cq.Workplane("YZ", (ED, -c.DIN_NARROW_HEIGHT/2 + 2.5, 5))
            .text(c.MODULE_NAME, 6, -0.3, kind="bold", halign="left"))
    else:
        text_name = dummy

    # ====================== lid =========================

    lid = (cq.Workplane("XY", (0, 0, EW))
        .placeSketch(sketch_inner.copy().wires().offset(1))
        .extrude(-CT)
    )
    for l in lid_screw_blocks:
        lid = lid.union(l, clean=True)
    for (x, y, z) in screw_positions:
        lid = (lid.faces(">Z").workplane()
            .moveTo(x, y)
            .cboreHole(c.SCREW_HOLE_DIAM + 0.4, c.SCREW_HEAD_DIAM,
                       c.SCREW_HEAD_DEPTH, c.SCREW_HOLE_DEPTH)
        )

    # Cut fan features from lid
    lid = lid.cut(fan_cutout).cut(fan_screw_cutout)

    # ====================== build case =========================

    case = (outer.cut(inner)
        .cut(clip_cutouts)
        .union(dividers)
        .cut(slot_cutouts)
        .union(shelves)
        .union(esp32_carriers)
        .union(wago_holders)
        .cut(usb_cutout)
        .cut(power_in_cutout)
        .cut(power_out_cutouts)
        .cut(vent_slots)
        .cut(wire_opening)
        .cut(text_brand)
        .cut(text_name)
        .cut(lid)
    )
    for b in case_screw_blocks:
        case = case.union(b)

    # ================================= export ======================

    results = {
        "case": case,
        "lid": lid,
    }
    for i, cl in enumerate(clips):
        results[f"clip_{i}"] = cl

    base_name = Path(os.path.basename(__file__)).stem + "_" + c.CONFIG_NAME

    for name in results:
        print(f"{name}: \n {results[name]} \n ")
        results[name].export(base_name + "_" + name + ".stl")

    # Assembly
    assembly = cq.Assembly(case).add(lid)
    for cl in clips:
        assembly = assembly.add(cl)

    assembly.export(base_name + "_assembly.step")
    compound = assembly.toCompound()
    compound.export(base_name + "_compound.step")

    print(f"Export complete: {base_name}")


def show():
    show_object(case)
    show_object(lid.translate((0, 0, 50)))
    for cl in clips:
        show_object(cl)
