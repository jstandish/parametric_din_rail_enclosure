"""
SK120 DIN Rail Card-Slot Enclosure Configuration

Houses 3 headless XY-SK120X DC-DC converters in vertical card slots,
with ESP32 bay for ESPHome control, parametric fan mount (rear-biased on lid),
and power distribution: DC input at bottom, outputs at top.
"""

import sys
sys.path.append('../')
from din_declarations import *

config = SK120Config(
    CONFIG_NAME="sk120_3x",

    # SK120 board dimensions (adjust after measuring bare board without display)
    sk120=SK120Board(
        pcb_width=50.0,        # along DIN rail
        pcb_height=81.0,       # vertical insertion
        component_depth=40.0,  # perpendicular to rail
        pcb_thickness=1.6,
        slot_clearance=0.3,
    ),
    num_boards=3,
    board_spacing=3.0,

    # ESP32 for ESPHome control via JST serial
    esp32=Board("top",
                board_width=18,
                length=24,
                thickness=2.0,
                usb_height=1.8,
                mount_height=1.5),
    esp32_section_width=30.0,

    # 40mm fan on lid, biased toward rear
    fan=Fan(size=40, screw_spacing=32.0, screw_diam=3.2),
    fan_offset_from_rear=5.0,

    # Power: in at bottom, out at top (DIN PSU convention)
    power_input=ScrewTerminal(pitch=5.08, poles=2),
    power_output=ScrewTerminal(pitch=5.08, poles=2),
    NR_WAGO_INTERNAL=2,  # V+ and V- splitters

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
