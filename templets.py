"""Layout templates for the album page generator.

Each layout function takes (page, margin, gutter) and returns a list of
(x, y, w, h) slot rectangles in page coordinates. The number of slots
dictates how many images a layout consumes.

To add a new template: write a layout_* function and register it in LAYOUTS.
"""

import random



def layout_hero_stack(page, margin, gutter):
    """Modern asymmetric collage: one tall hero + two stacked (3 images)."""
    content = page - 2 * margin
    left_w = int(content * 0.58)            # hero column width
    right_w = content - left_w - gutter     # secondary column width
    right_h = (content - gutter) // 2       # each stacked slot height

    return [
        (margin, margin, left_w, content),                              # hero (tall)
        (margin + left_w + gutter, margin, right_w, right_h),           # top-right
        (margin + left_w + gutter, margin + right_h + gutter,
         right_w, content - right_h - gutter),                          # bottom-right
    ]


def layout_triptych(page, margin, gutter):
    """Three equal portrait images in a horizontal row (3 images).

    Inspired by a classic gallery triptych: equal columns, generous white
    space above and below, vertically centered on the page.
    """
    content = page - 2 * margin
    slot_w = (content - 2 * gutter) // 3
    slot_h = int(slot_w * 4 / 3)            # portrait 3:4 ratio
    slot_h = min(slot_h, content)           # never exceed the content height
    y = (page - slot_h) // 2                # center the row vertically

    return [
        (margin + i * (slot_w + gutter), y, slot_w, slot_h)
        for i in range(3)
    ]


def layout_single(page, margin, gutter):
    """One landscape image centered on a wide white mat (1 image).

    Inspired by a single matted/framed print: lots of surrounding whitespace.
    """
    mat = int(page * 0.12)                  # generous mat (overrides margin)
    slot_w = page - 2 * mat
    slot_h = int(slot_w * 2 / 3)            # landscape 3:2 ratio
    y = (page - slot_h) // 2                # center vertically

    return [(mat, y, slot_w, slot_h)]


# Registry of available layouts (name -> function).
LAYOUTS = {
    "hero_stack": layout_hero_stack,
    "triptych": layout_triptych,
    "single": layout_single,
}


def define_slots(page, margin, gutter, layout):
    """Resolve a layout name (or "random") into (name, slot rectangles)."""
    name = random.choice(list(LAYOUTS)) if layout == "random" else layout
    if name not in LAYOUTS:
        raise ValueError(f"Unknown layout '{name}'. Options: {list(LAYOUTS)}")
    return name, LAYOUTS[name](page, margin, gutter)
