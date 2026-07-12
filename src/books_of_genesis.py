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

def inject_custom_book(ram_substrate, size, text):
    """
    Randomly injects a custom string (or chunk of a book) into the RAM.
    """
    if not text:
        return
    book_bytes = [ord(c) for c in text if 32 <= ord(c) <= 126]
    if not book_bytes:
        return
        
    start = random.randint(0, size - len(book_bytes) - 1)
    
    for i, b in enumerate(book_bytes):
        # Don't overwrite existing food (0x55) or traps (0xFF)
        if ram_substrate[start + i] not in (0x55, 0xFF):
            ram_substrate[start + i] = b
            
    return start, len(book_bytes), text

def inject_passage(ram_substrate, size, category, book_name):
    """
    Inject a whole book file as ONE contiguous passage (a "page") at a random location.

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
    return inject_custom_book(ram_substrate, size, text)

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
