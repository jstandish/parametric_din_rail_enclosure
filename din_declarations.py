# ==========================================================================================
# This is NOT the config file !!
# Do not modify this file, actual configuration resides in config.py
# Please adapt config.py to meet your needs
#
# Copyright @infradom
# ===========================================================================================

from dataclasses import dataclass, field

@dataclass
class Led:
    x: float # from lower left component-side corner of board
    y: float # from lower_left component-side corner of board
    txt: str = ""
    
# front board  : usb up orientation(if any) 
# top board    : usb up orientation
# bottom board : usb down orientation

@dataclass
class Board:
    position:     str # either "top" | "bottom"| "front"
    board_width:  float  # excluding optional JST XH connectors
    length:       float
    thickness:    float = 1.5
    usb_height:   float | None = None   # center to under side of board; None if no usb required
    mount_height: float = 0 # from inner floor of case to under side of board
                            # id position = front: vertical board: front to upper side of board
    jst_extrawidth_left:  float = 0     # jst xh connector may extend beyond border e.g. 2 mm
    jst_extrawidth_right: float = 0     # jst xh connector may extend beyond border e.e. 2 mm
    leds:         list  | None = None   # list of Led declarations

    @property
    def width(self): return self.board_width + self.jst_extrawidth_left + self.jst_extrawidth_right

    @property
    def usb_offset(self): return (self.jst_extrawidth_left - self.jst_extrawidth_right)/2

# 
# 
# ============================= DO NOT MODIFY THESE DEFAULTS; they can be overridden in the config.py file
#
@dataclass
class Config: # DO NOTY MODIFY !!! adapt corresponding entries in config.py
    CONFIG_NAME:        str       = "modbus1"
    board1:   callable = field(default_factory = lambda: Board("front",  board_width=16,   length=43.4, thickness=2.0, usb_height = None, mount_height = 12, # vertical board behind front
                         leds= [ Led( x=1.4, y=21.0, txt=""), Led( x=3.8, y=21.0, txt="")] )   )              # vertical board behind front
    board2:   callable = field(default_factory = lambda: Board("top", board_width=26, length=35, thickness=2.0, usb_height = 1.8,  mount_height = 2.5, # mini C3 or S3 board
                         jst_extrawidth_left = 0.0) )
    board3:   callable = field(default_factory= lambda: Board("bottom",    board_width=18,   length=24, thickness=2.0, usb_height = 1.8,  mount_height = 1.5, # 23.2 length for C3 zero; 24 length for S3 zerp
                         jst_extrawidth_right = 0.0) )

    BRAND:              str       = "@infradom"

    MODULE_NAME:        str       =  None # "modbus1"
    NR_WAGO_TOP:        int       =  0    # number of wago 221 at top
    NR_WAGO_BOTTOM:     int       =  2    # number of wago 221 at bottom
    WAGO_UPPER_TEXT:    list      =  field(default_factory=lambda: []) # list of strings - single character strings recommended
    WAGO_LOWER_TEXT:    list      =  field(default_factory=lambda: ["A", "B"]) #["5", "0", ] # list of strings - single character strings recommended
    CASE_WIDTH:         float     = 18    # standard unit = 18 mm - unless wago count makes it wider
    CASE_THICKNESS:     float     =  2    # untested if you modify this

    SCREW_HOLE_DIAM:    float   =  3      # diameter of hole for screw body (thread diam)
    SCREW_HEAD_DIAM:    float   =  5.6    # diameter of the hole for screw head
    SCREW_HEAD_DEPTH:   float   =  2.5
    SCREW_INSERT_DIAM:  float   =  4.3    # set equal to SCREW_HOLE_DIAM if working without insert
    SCREW_INSERT_DEPTH: float   =  4.1
    SCREW_HOLE_DEPTH:   float   =  12
    SCREW_BLOCK_SIZE:   float   =  7.0
    SCREW_LID_EXTRA:    float   =  3.5

    WAGO_TXT_SIZE:      float   = 4

    # ================ DIN RAIL - QUASI FIXED DIMENTIONS =========
    # usually no need to modify
    DIN_HEIGHT:        float = 82    # can be modified slightly
    DIN_DEEP_HIGH:     float = 55    # typical 60 - can be modified slightly
    DIN_DEEP_LOW:      float = 47    # almost no room for modification (if board 1 is installed)
    DIN_NARROW_HEIGHT: float = 45    # fixed - visible front height
    DIN_RAIL_LOWER:    float = 18.7  # fixed - between middle of front and bottom of rail
    DIN_RAIL_UPPER:    float = 17    # fixed - etween middle of front and top of rail

    # OTHER QUASI FIXED DIMENSIONS
    WAGO_OFFSET:       float = 7.88
    WAGO_FIX_WIDTH:    float = 5.0
    WAGO_LIP_LENGTH:   float = 13
    WAGO_HEIGHT:       float = 8.5
    WAGO_LENGTH:       float = 35

    # USB-C cutout dimension
    USB_WIDTH:         float = 9.3 # 9.1
    USB_HEIGHT:        float = 3.3 # 3.3 some margin for easy insertion

    BOARD_FIX_WIDTH:      float= 2.2
    LIGHT_GUIDE_DIAMETER: float = 2.0
    LIGHT_CARRIER_DIAM:   float = LIGHT_GUIDE_DIAMETER+1.3


# ============================= SK120 Card-Slot Enclosure Declarations =============================
# Form factor: Bernic High/Low style (two-piece: base + front cover)
#
# Side profile (stair-step):
#
#        [6-port output terminals]
#   ┌────────┬─────────────┐
#   │ BASE   │ FRONT COVER │  ← cover compression-fits over base
#   │ (low)  │ (high)      │     contains ESP32 electronics bay
#   │ SK120  │             │
#   │ boards │   fan       │
#   │ in     │             │
#   │ slots  │             │
#   └────────┴─────────────┘
#        [2-port input terminal]
#   ══DIN RAIL══
#   back(rail)    front→

@dataclass
class SK120Board:
    """Headless XY-SK120X board for card-slot mounting (display removed).
    Boards lie flat (horizontal), stacked vertically, slide in from front."""
    pcb_width: float = 50.0        # narrow edge, along DIN rail (Z axis)
    pcb_length: float = 81.0       # long edge, depth from rail (X axis, slide-in direction)
    component_height: float = 20.0 # height of components above PCB when lying flat (Y axis)
    pcb_thickness: float = 1.6     # PCB edge thickness gripped by slot
    slot_clearance: float = 0.3    # extra play in slot groove

@dataclass
class Fan:
    """Parametric square fan cutout"""
    size: float = 40.0            # fan width/height (25, 30, 40, 50, 60, 80mm)
    screw_spacing: float = 32.0   # hole-to-hole distance
    screw_diam: float = 3.2       # mounting screw hole diameter
    depth: float = 10.0           # fan body thickness (for lid recess)

@dataclass
class ScrewTerminal:
    """Green screw terminal block"""
    pitch: float = 5.08           # pin-to-pin spacing
    poles: int = 2                # number of poles
    height: float = 8.5           # terminal block height
    depth: float = 7.0            # how far it protrudes

    @property
    def width(self): return self.pitch * self.poles

@dataclass
class SK120Config:
    CONFIG_NAME:        str = "sk120_3x"

    # SK120 boards
    sk120:    callable = field(default_factory=lambda: SK120Board())
    num_boards:       int   = 3
    board_spacing:    float = 3.0    # divider thickness between card slots

    # Card slot guide
    slot_depth:       float = 3.0    # how deep PCB edge sits in groove
    slot_wall:        float = 2.0    # wall thickness of slot guide rails

    # ESP32 section (in front cover electronics bay)
    esp32:    callable = field(default_factory=lambda: Board("top", board_width=18, length=24, thickness=2.0, usb_height=1.8, mount_height=1.5))

    # Fan (on top of front cover, biased toward rear/DIN rail)
    fan:      callable = field(default_factory=lambda: Fan())
    fan_offset_from_rear: float = 5.0

    # Power input (bottom) - single 2-pole green screw terminal
    power_input:  callable = field(default_factory=lambda: ScrewTerminal(poles=2))
    # Power output (top) - 6-port (3 pairs of +/-) terminal block
    power_output: callable = field(default_factory=lambda: ScrewTerminal(poles=6))
    # Internal WAGO 221 splitters (V+ and V-)
    NR_WAGO_INTERNAL: int = 2

    # Base part dimensions
    CASE_THICKNESS:     float = 2.0
    COMPRESSION_LIP:    float = 1.5   # lip height for compression fit
    COMPRESSION_GAP:    float = 0.2   # clearance for compression fit

    # Front cover (electronics bay) depth beyond base
    COVER_DEPTH:        float = 30.0  # how far the front cover extends beyond the base

    BRAND:              str   = "@jstandish"
    MODULE_NAME:        str   = "SK120x3"

    # DIN rail standard dimensions
    DIN_HEIGHT:         float = 82.0
    DIN_NARROW_HEIGHT:  float = 45.0
    DIN_RAIL_LOWER:     float = 18.7
    DIN_RAIL_UPPER:     float = 17.0

    # Screws
    SCREW_HOLE_DIAM:    float = 3.0
    SCREW_HEAD_DIAM:    float = 5.6
    SCREW_HEAD_DEPTH:   float = 2.5
    SCREW_INSERT_DIAM:  float = 4.3
    SCREW_INSERT_DEPTH: float = 4.1
    SCREW_HOLE_DEPTH:   float = 12.0
    SCREW_BLOCK_SIZE:   float = 7.0
    SCREW_LID_EXTRA:    float = 3.5

    # WAGO (reused for internal splitters)
    WAGO_OFFSET:        float = 7.88
    WAGO_FIX_WIDTH:     float = 5.0
    WAGO_HEIGHT:        float = 8.5
    WAGO_LENGTH:        float = 35.0

    @property
    def enclosure_width(self):
        """Total width along DIN rail (Z axis)"""
        return self.sk120.pcb_width + 2 * self.CASE_THICKNESS

    @property
    def base_depth(self):
        """Base depth from DIN rail (X axis) — holds SK120 boards"""
        return self.sk120.pcb_length + 2 * self.CASE_THICKNESS + self.slot_depth

    @property
    def total_depth(self):
        """Total depth including front cover electronics bay"""
        return self.base_depth + self.COVER_DEPTH

    @property
    def enclosure_height(self):
        """Total height (Y axis) — boards stacked vertically"""
        board_stack = self.num_boards * (self.sk120.component_height + self.sk120.pcb_thickness + self.board_spacing)
        return board_stack + self.board_spacing + 2 * self.CASE_THICKNESS
