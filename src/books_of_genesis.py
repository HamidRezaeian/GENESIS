import random
import numpy as np
import os
import glob

def get_library_books():
    """Returns a structured list of available curriculum files in the Books/ directory."""
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Books")
    books = {}
    if not os.path.exists(base_dir):
        return books
        
    for cat in os.listdir(base_dir):
        cat_path = os.path.join(base_dir, cat)
        if os.path.isdir(cat_path):
            books[cat] = []
            for file in os.listdir(cat_path):
                if file.endswith(".txt"):
                    books[cat].append(file.replace(".txt", ""))
    return books

def inject_custom_book(ram_substrate, size, text, at=None):
    """
    Injects a custom string (or chunk of a book) into RAM as one contiguous passage.

    `at` (optional) pins the start address; otherwise the passage lands at a random location.
    Pinning is what lets the library REGROW IN PLACE (see regrow_passage) instead of teleporting to
    a fresh random spot every restock — reading is destructive (a solved symbol is reclaimed to
    0x00), so a grazed passage must renew where it was grazed or the readers are left in the vacuum
    hole they ate while the new text appears across the ring (Result Exp 8: enc_frac collapse).
    """
    if not text:
        return
    book_bytes = [ord(c) for c in text if 32 <= ord(c) <= 126]
    if not book_bytes:
        return

    if at is None:
        start = random.randint(0, size - len(book_bytes) - 1)
    else:
        start = max(0, min(int(at), size - len(book_bytes) - 1))

    for i, b in enumerate(book_bytes):
        # Don't overwrite existing food (0x55) or traps (0xFF)
        if ram_substrate[start + i] not in (0x55, 0xFF):
            ram_substrate[start + i] = b

    return start, len(book_bytes), text

def inject_passage(ram_substrate, size, category, book_name, at=None):
    """
    Inject a whole book file as ONE contiguous passage (a "page"). `at` pins the start (used by
    regrow_passage to renew the library in place); default random location.

    Unlike inject_curriculum_file (which scatters single-word fragments uniformly), this keeps the
    text as a dense, contiguous readable region. The world then has real spatial structure —
    library "pages" of symbols surrounded by empty RAM — instead of a uniform confetti flood. That
    structure is what makes reading a navigable skill (a text-density gradient a seeking organism
    can climb toward), i.e. a real library rather than a video-game where every tile is edible.
    Returns (start, length, text) or None. Skips existing food (0x55) / traps (0xFF) byte-wise.
    """
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Books")
    file_path = os.path.join(base_dir, category, book_name + ".txt")
    if not os.path.exists(file_path):
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    return inject_custom_book(ram_substrate, size, text, at)


def contiguous_library_start(size, target_bytes):
    """Fixed, centred start address of the contiguous library block. Stable across restocks so the
    shelf REGROWS IN PLACE at the same location instead of teleporting each time (a stable pinned
    start is what lets readers keep grazing the same continuous scroll)."""
    tb = int(min(max(1, target_bytes), size - 1))
    return max(0, (size - tb) // 2)


def inject_contiguous_library(ram_substrate, size, category, book_name, target_bytes, at=None):
    """Lay the curriculum as ONE CONTIGUOUS SCROLL of `target_bytes` printable symbols (a real page
    of continuous text), tiling the book file end-to-end until the block is filled, pinned at a fixed
    centred start so restocks renew it IN PLACE.

    WHY (Result Exp 11, 2026-07-12): the previous library was many short passages (one 52-byte
    alphabet file per inject_passage) scattered at random anchors — "confetti". A reading organism
    saccades +1 symbol-to-symbol along text it decodes (Exp 9), so it walks to the END of a short
    fragment and then steps into VACUUM, earning nothing while it crosses the gap to the next
    fragment. Half the colony was thus always in transit (encounter fraction ~0.5), and that idle
    off-text burn — not the exchange rate — is what kept the reading economy net-negative at every
    density (readers could not out-earn the gaps). Laying the SAME bytes as one contiguous scroll
    lifts encounter to ~0.98: a saccading reader almost never leaves the text, so reading income
    finally exceeds metabolism and the population grows on reading alone (native reproduction) to the
    world's carrying capacity instead of bleeding to the refuge floor. This is pure world STRUCTURE —
    no reward constant, no exchange-rate change, and arguably more faithful to reading an actual book
    (continuous lines) than scattered word-confetti. Returns (start, length)."""
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Books")
    file_path = os.path.join(base_dir, category, book_name + ".txt")
    if not os.path.exists(file_path):
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    glyphs = [ord(c) for c in text if 32 <= ord(c) <= 126]
    if not glyphs:
        return None
    tb = int(min(max(1, target_bytes), size - 1))
    start = contiguous_library_start(size, tb) if at is None else max(0, min(int(at), size - tb - 1))
    for i in range(tb):
        p = start + i
        if p >= size:
            break
        # Preserve food (0x55) and traps (0xFF); the scroll fills every other cell in the block.
        if ram_substrate[p] not in (0x55, 0xFF):
            ram_substrate[p] = glyphs[i % len(glyphs)]
    return start, tb


def regrow_passage(ram_substrate, size, category, book_name, radius=64):
    """Restock the library IN PLACE: grow the next passage adjacent to text that already exists,
    so the readable region stays one persistent, contiguous shelf near the organisms grazing it,
    rather than a fresh random page teleported across the ring each restock. Because reading is
    destructive (a solved symbol -> 0x00), non-local restock strands a colony in the vacuum it ate
    while its food reappears elsewhere (Result Exp 8: enc_frac -> 0). Picks a random existing text
    cell as the anchor and injects a short offset away; falls back to a random location (old
    behaviour) when the substrate holds no text yet (first stock)."""
    import numpy as np
    text_idx = np.flatnonzero((ram_substrate >= 32) & (ram_substrate <= 126)
                              & (ram_substrate != 0x55) & (ram_substrate != 0xFF))
    at = None
    if text_idx.size:
        anchor = int(text_idx[random.randint(0, text_idx.size - 1)])
        at = (anchor + random.randint(-radius, radius)) % size
    return inject_passage(ram_substrate, size, category, book_name, at=at)

def inject_curriculum_file(ram_substrate, size, category, book_name):
    """
    Reads a book file, breaks it into words/chunks, and scatters them across the universe.
    """
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Books")
    file_path = os.path.join(base_dir, category, book_name + ".txt")
    
    if not os.path.exists(file_path):
        return 0
        
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Chunking: Break by spaces or newlines to create digestible fragments
    fragments = [f.strip() for f in content.split() if f.strip()]
    
    injected_count = 0
    # Inject each fragment multiple times so they are easier to find
    for frag in fragments:
        for _ in range(3): # 3 copies of each fragment
            inject_custom_book(ram_substrate, size, frag)
            injected_count += 1
            
    return injected_count
