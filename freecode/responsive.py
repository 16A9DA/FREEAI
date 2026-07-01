import shutil


def get_terminal_width():
    """Live terminal width, read fresh each call (user can resize any time)."""
    return shutil.get_terminal_size((80, 24)).columns


def tier():
    """Width tier: 'narrow' <80, 'normal' 80-120, 'wide' >120."""
    w = get_terminal_width()
    if w < 80:
        return "narrow"
    if w <= 120:
        return "normal"
    return "wide"


def is_narrow():
    return tier() == "narrow"
