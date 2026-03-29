"""
SK120 DIN Rail Card-Slot Enclosure Configuration
Bernic High/Low form factor (two-piece: base + front cover)

Base (low): DIN rail clip, 3 SK120 boards in horizontal card slots,
  6-port output terminal (top), 2-port input terminal (bottom).
Front cover (high): compression-fits over base, ESP32 electronics bay, fan.
"""

import sys
sys.path.append('../')
from din_declarations import *

config = SK120Config(
    CONFIG_NAME="sk120_3x",

    # SK120 board dimensions (adjust after measuring bare board without display)
    sk120=SK120Board(
        pcb_width=50.0,          # narrow edge along DIN rail (Z)
        pcb_length=81.0,         # long edge, slide-in direction (X)
        component_height=20.0,   # component height above PCB when flat (Y)
        pcb_thickness=1.6,
        slot_clearance=0.3,
    ),
    num_boards=3,
    board_spacing=3.0,

    # ESP32 in front cover electronics bay
    esp32=Board("top",
                board_width=18,
                length=24,
                thickness=2.0,
                usb_height=1.8,
                mount_height=1.5),

    # 40mm fan on top of front cover, biased toward rear
    fan=Fan(size=25, screw_spacing=20.0, screw_diam=3.2),
    fan_offset_from_rear=2.0,

    # Power: 2-pole input (bottom), 6-port output (top) — 3 pairs +/-
    power_input=ScrewTerminal(pitch=5.08, poles=2),
    power_output=ScrewTerminal(pitch=5.08, poles=6),
    NR_WAGO_INTERNAL=2,  # V+ and V- splitters

    # Front cover (electronics bay) extends 30mm beyond base
    COVER_DEPTH=30.0,
    COMPRESSION_LIP=1.5,
    COMPRESSION_GAP=0.2,

    BRAND="@jstandish",
    MODULE_NAME="SK120x3",
    CASE_THICKNESS=2.0,
)

# ======================================= END of the config part =================================
import cadquery as cq
import din_enclosure_sk120
if 'show_object' not in globals():
    def show_object(*args, **kwargs):
        pass

din_enclosure_sk120.generate_enclosure(config)
din_enclosure_sk120.show_object = show_object
din_enclosure_sk120.show()
