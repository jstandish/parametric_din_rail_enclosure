# SK120 DIN Rail Card-Slot Enclosure Plan

## Context

The forked parametric DIN rail enclosure project currently builds enclosures for small ESP boards (18mm wide, 1 DIN unit). We need to adapt it for **3 headless XY-SK120X DC-DC converters** controlled via ESPHome over their JST serial connectors. The boards slide vertically into card-slot guides — no screw mounting through the back. An ESP32 section, parametric fan, and shared two-pole screw terminal input are also required.

## SK120 Board Dimensions (Parametric Defaults)

With display removed, estimated bare board:
- **PCB width**: 50mm (along DIN rail — this is the card slot width)
- **PCB height**: 81mm (vertical, insertion direction)
- **Component depth**: 40mm (perpendicular to rail, how far components protrude)
- **PCB thickness**: 1.6mm (what the card slot grooves grip)

All dimensions are parametric in config and easily adjusted once boards are measured.

## Architecture Approach

Create a **new config + new generator function** rather than refactoring the existing `generate_enclosure()`. The existing code is tightly coupled to its 3-board horizontal/vertical layout and DIN clip geometry. We will:

1. Add new dataclasses to `din_declarations.py` for the SK120 card-slot design
2. Create a new `din_enclosure_sk120.py` generator
3. Create `sk120/config.py` as the entry point

This avoids mass refactoring while reusing the DIN clip generation code (extracted as a callable).

## Files to Create/Modify

### 1. `din_declarations.py` — Add new dataclasses (append, don't modify existing)

```python
@dataclass
class SK120Board:
    """Headless SK120 board for card-slot mounting"""
    pcb_width: float = 50.0       # along DIN rail (slot width)
    pcb_height: float = 81.0      # vertical (insertion direction)
    component_depth: float = 40.0 # perpendicular to rail
    pcb_thickness: float = 1.6    # thickness the slot grips
    slot_clearance: float = 0.3   # extra play in slot groove

@dataclass
class Fan:
    """Parametric fan cutout"""
    size: float = 40.0            # fan width/height (square fans: 25, 30, 40, 50, 60, 80mm)
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
    CONFIG_NAME: str = "sk120_3x"

    # SK120 boards
    sk120: SK120Board (default_factory)
    num_boards: int = 3
    board_spacing: float = 3.0    # wall thickness between card slots

    # Card slot guide
    slot_depth: float = 3.0       # how deep the PCB edge sits in the groove
    slot_wall: float = 2.0        # wall thickness of slot guide rails

    # ESP32 section
    esp32: Board (reuse existing Board class for the ESP32)
    esp32_section_width: float = 30.0  # width along rail for ESP32 bay

    # Fan
    fan: Fan (default_factory)
    fan_offset_from_rear: float = 5.0  # bias toward DIN rail (rear)

    # Power input (bottom) — single 2-pole green screw terminal
    power_input: ScrewTerminal (default_factory, poles=2)

    # Power output (top) — one 2-pole terminal per SK120 board
    power_output: ScrewTerminal (default_factory, poles=2)

    # Internal WAGO 221 splitters (V+ and V-)
    NR_WAGO_INTERNAL: int = 2     # one for V+, one for V-

    # Case
    CASE_THICKNESS: float = 2.0
    BRAND: str = "@jstandish"
    MODULE_NAME: str = "SK120x3"

    # DIN rail (reuse standard dims)
    DIN_HEIGHT: float = 82.0
    DIN_NARROW_HEIGHT: float = 45.0
    DIN_RAIL_LOWER: float = 18.7
    DIN_RAIL_UPPER: float = 17.0

    # Screws (reuse existing defaults)
    SCREW_HOLE_DIAM: float = 3.0
    SCREW_HEAD_DIAM: float = 5.6
    SCREW_HEAD_DEPTH: float = 2.5
    SCREW_INSERT_DIAM: float = 4.3
    SCREW_INSERT_DEPTH: float = 4.1
    SCREW_HOLE_DEPTH: float = 12.0
    SCREW_BLOCK_SIZE: float = 7.0
    SCREW_LID_EXTRA: float = 3.5
```

### 2. `din_enclosure_sk120.py` — New generator (~400 lines)

**Overall enclosure dimensions** (computed from config):
- **Width along rail** = `num_boards * sk120.pcb_width + (num_boards+1) * board_spacing + esp32_section_width + 2 * CASE_THICKNESS`
  - ≈ 3×50 + 4×3 + 30 + 4 = **196mm** (~11 DIN units)
- **Height** = `DIN_HEIGHT` = 82mm (standard DIN profile)
- **Depth** = `sk120.component_depth + 2*CASE_THICKNESS + slot_depth` ≈ 47mm

**Key modules/functions to implement:**

#### a) `generate_din_clip()` — Extract/reuse from existing code
- Reuse the existing DIN clip geometry from `din_enclosure.py` lines 50-98
- May need multiple clips spaced along the wider enclosure (e.g. 2-3 clips)

#### b) `generate_card_slots(config)` — Card slot guide rails
- For each of `num_boards` positions, create paired vertical grooves
- Each groove is a channel in the enclosure wall: `pcb_thickness + slot_clearance` wide × `slot_depth` deep
- Grooves run the full internal height, open at top for board insertion
- Bottom of each slot has a small shelf/stop so the board rests at the correct height
- Walls between slots are `board_spacing` thick

#### c) `generate_fan_mount(config)` — Parametric fan on lid, rear-biased
- Square cutout in lid: `fan.size × fan.size`
- 4 screw holes at `fan.screw_spacing` square pattern
- Positioned on the lid biased toward the rear (DIN rail side)
- Grid/finger guard pattern (optional, parametric)

#### d) `generate_esp32_bay(config)` — ESP32 section at one end
- Separate bay at one end of the enclosure
- Reuse existing `Board` class and `board_fix()` clip pattern for mounting
- USB cutout on the top or side for programming
- Wiring channel/opening between ESP32 bay and SK120 slots for JST cables

#### e) `generate_power_layout(config)` — Power distribution system

**Input (bottom):** Two-pole green screw terminal block for DC input.

**Internal distribution:** Two internal WAGO 221 connectors (one for V+, one for V-) split the single input to feed all 3 SK120 VIN+/VIN- pairs.

**Output (top):** Standard green screw terminal blocks — one pair (OUT+/OUT-) per SK120 board, accessible from the top face.

Follows standard DIN rail PSU convention: **power in at bottom, power out at top.**

#### f) `generate_case_body(config)` — Main enclosure
- Wide rectangular body with DIN rail profile on back
- Internal dividers creating card slot channels
- Open top for board insertion (lid closes it)
- Ventilation slots on sides for airflow (fan pulls through)

#### g) `generate_lid(config)` — Top lid
- Covers the top, holds boards in place once closed
- Fan mount integrated
- Screw holes for assembly

### 3. `sk120/config.py` — New config entry point

```python
import sys
sys.path.append('../')
from din_declarations import *

config = SK120Config(
    CONFIG_NAME="sk120_3x",
    sk120=SK120Board(),        # default dims, adjust after measuring
    num_boards=3,
    esp32=Board("top", board_width=18, length=24, thickness=2.0,
                usb_height=1.8, mount_height=1.5),
    fan=Fan(size=40),          # 40mm fan default
    power_terminal=ScrewTerminal(),
)

import din_enclosure_sk120
din_enclosure_sk120.generate_enclosure(config)
```

## Card Slot Mechanical Design Detail

```
     Top (open for insertion)
     ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐
     │▓▓│  │▓▓│  │▓▓│  │▓▓│  │▓▓│  │▓▓│   ← slot guide walls
     │▓▓│  │▓▓│  │▓▓│  │▓▓│  │▓▓│  │▓▓│
     │  ├──┤  │  │  ├──┤  │  │  ├──┤  │   ← PCB edges in grooves
     │  │SK│  │  │  │SK│  │  │  │SK│  │
     │  │12│  │  │  │12│  │  │  │12│  │   ← SK120 boards
     │  │0 │  │  │  │0 │  │  │  │0 │  │
     │  │#1│  │  │  │#2│  │  │  │#3│  │
     │  ├──┤  │  │  ├──┤  │  │  ├──┤  │
     │▓▓│  │▓▓│  │▓▓│  │▓▓│  │▓▓│  │▓▓│
     └──┘  └──┘  └──┘  └──┘  └──┘  └──┘
     ════════════════════════════════════   ← bottom shelf/stop

     Side view (looking from end):

            OUT+/OUT- (top, per board)
     ┌─────────────────────────┐  ← lid w/ fan (rear-biased)
     │  ┌────┐ ┌────┐ ┌────┐  │
     │  │ SK │ │ SK │ │ SK │  │
     │  │120 │ │120 │ │120 │  │  ← boards in card slots
     │  │ #1 │ │ #2 │ │ #3 │  │
     │  └────┘ └────┘ └────┘  │
     └─────────────────────────┘
            VIN+/VIN- (bottom, shared 2-pole screw terminal)

     Cross-section looking from above:

     DIN RAIL (back)
     ┌─────────────────────────────────────┐
     │ case wall                           │
     │  ┌─┐   ┌─┐   ┌─┐   ┌─┐   ┌──────┐ │
     │  │g│ 1 │g│ 2 │g│ 3 │g│   │ ESP32│ │
     │  │r│   │r│   │r│   │r│   │      │ │
     │  │o│   │o│   │o│   │o│   │      │ │
     │  │o│   │o│   │o│   │o│   └──────┘ │
     │  │v│   │v│   │v│   │v│            │
     │  │e│   │e│   │e│   │e│            │
     │  └─┘   └─┘   └─┘   └─┘            │
     │ case wall                           │
     └─────────────────────────────────────┘
     FRONT (facing out from rail)
```

Each groove is a simple channel: `pcb_thickness + 0.3mm clearance` wide × `slot_depth` deep, running vertically. The board PCB edges slide into these grooves. Components face into the open channel between groove pairs.

## Power Distribution Layout

```
                         TOP (outputs)
     ┌──────────┬──────────┬──────────┐
     │[OUT+ OUT-]│[OUT+ OUT-]│[OUT+ OUT-]│  ← 3x green screw terminal blocks
     │  SK120 #1 │  SK120 #2 │  SK120 #3 │
     │           │           │           │
     │  VIN+ VIN-│  VIN+ VIN-│  VIN+ VIN-│
     └─────┬─┬───┴─────┬─┬───┴─────┬─┬───┘
           │ │         │ │         │ │
           │ │         │ │         │ │      internal wiring
           │ └────┐    │ └────┐    │ └────┐
           └───┐  │    └───┐  │    └───┐  │
               │  │        │  │        │  │
          ┌────┴──┴────────┴──┴────────┴──┴────┐
          │  WAGO 221 (V+)    WAGO 221 (V-)    │  ← 2x internal WAGO splitters
          │  (1-in, 3-out)    (1-in, 3-out)    │    (mounted inside enclosure)
          └────────┬──────────────┬─────────────┘
                   │              │
              ┌────┴──────────────┴────┐
              │  [DC IN+]    [DC IN-]  │  ← 1x two-pole green screw terminal
              └────────────────────────┘
                      BOTTOM (input)
```

**Components:**
- **Bottom input:** 1x two-pole green screw terminal block (5.08mm pitch) — DC power in
- **Internal split:** 2x WAGO 221-413 (3-way) or 221-415 (5-way) — one for V+, one for V-
- **Top outputs:** 3x two-pole green screw terminal blocks (5.08mm pitch) — one per SK120
- **WAGO mounting:** Internal WAGO holders reuse the existing `wago_fix()` pattern from `din_enclosure.py`

## Verification

1. Run `python sk120/config.py` — should generate STL and STEP files without errors
2. Open STL in slicer or CAD viewer:
   - Confirm 3 card slots with correct spacing
   - Confirm boards slide in from top
   - Confirm fan cutout on lid, rear-biased
   - Confirm ESP32 bay at end
   - Confirm screw terminal cutout
   - Confirm DIN rail clip(s) on back
3. Check that existing configs (`dual/config.py` etc.) still work unchanged
