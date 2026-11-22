SWITCH_CATEGORIES = [
    ('l', 'Linear'),
    ('sl', 'Silent Linear'),
    ('t', 'Tactile'),
    ('st', 'Silent Tactile'),
    ('c', 'Clicky'),
]

# category -> css data-switch value for the colored dots and stats bars (silent ones draw hollow)
SWITCH_KINDS = {
    'l': 'linear',
    'sl': 'silent-linear',
    't': 'tactile',
    'st': 'silent-tactile',
    'c': 'clicky',
}

SWITCH_STEMS = [
    ('mx', 'MX'),
    ('topre', 'Topre'),
    ('alps', 'Alps'),
]

SWITCH_MATERIALS = [
    ('abs', 'ABS'),
    ('nylon', 'Nylon'),
    ('pc', 'Polycarbonate'),
    ('pe', 'Polyethylene'),
    ('pom', 'POM'),
]


# tabs on the keyboards page, keyed by the row's data-type
KEYBOARD_KINDS = {
    'prebuilt': 'Prebuilts',
    'custom': 'Customs',
}

WIRED = 'Wired'
WIRELESS = 'Wireless'
BLUETOOTH = 'Bluetooth'
CONNECTIVITY = [WIRED, WIRELESS, BLUETOOTH]

STOCK_PREBUILT_FACETS = [
    ('brand', 'Brand', None),
    ('size', 'Size', None),
    ('layout', 'Layout', None),
    ('connectivity', 'Connectivity', CONNECTIVITY),
]

ICON_FIELDS = ['lubed', 'filmed', 'flex_cuts', 'half']

COMBINED_FIELDS = {
    'force': ('peak_force', 'bottom_out_force'),
    'housing': ('top_housing', 'bottom_housing'),
}

FIELD_LABELS = {
    'pcb': 'PCB',
    'category': 'Type',
    'half': 'Half plate',
    'force': 'Peak / bottom out force',
    'travel_distance': 'Travel',
    'housing': 'Housing',
}

# htmx event the page dialogs listen for to close themselves after a save
CLOSE_DIALOG_EVENT = 'close-dialog'

STOCK_UPLOAD_MAX_BYTES = 2 * 1024 * 1024

MAX_ID_DIGITS = 18
MAX_QUANTITY = 2_147_483_647
QUANTITY_ERROR = f'Enter a whole number from 1 to {MAX_QUANTITY:,}.'

QUICK_ACTIONS = [
    {
        'label': 'New custom build',
        'description': 'Put a board together from parts',
        'icon': 'fas fa-screwdriver-wrench',
        'url_name': 'inventory_keyboards',
        'add': 'custom',
    },
    {
        'label': 'Add a prebuilt',
        'description': 'Pick one from the catalog',
        'icon': 'fas fa-hammer',
        'url_name': 'inventory_keyboards',
        'add': 'prebuilt',
    },
    {
        'label': 'Add switches',
        'description': 'Log a new batch of switches',
        'icon': 'fas fa-plus',
        'url_name': 'inventory_parts',
        'add': 'switch',
    },
    {
        'label': 'Add a part',
        'description': 'Kits, keycaps, plates, stabs',
        'icon': 'fas fa-cubes-stacked',
        'url_name': 'inventory_parts',
        'add': '',
    },
]

DEFAULT_PART_SOURCE = 'smart'
PART_SOURCE_DEFAULTS = {
    'smart': (
        'Smart',
        'Prefer parts in inventory first, then stock.',
    ),
    'stock': ('Stock', 'Pick from the catalog.'),
    'custom': ('Custom', 'Enter the details yourself.'),
}

STATS_BREAKDOWN_ROWS = 5

TYPING_RACE_WORDS = 25
TYPING_RACE_WORD_CHOICES = (25, 50, 100, 250)
TYPING_CHARS_PER_WORD = 5
TYPING_MAX_WPM = 400
TYPING_MAX_CHARACTERS = 5_000
TYPING_MAX_DURATION_MS = 3_600_000
TYPING_RECENT_RACES = 5
TYPING_SPARKLINE_RACES = 30
TYPING_SPARKLINE_MIN_WPM_RANGE = 20
TYPING_SPARKLINE_WIDTH = 120
TYPING_SPARKLINE_HEIGHT = 32
TYPING_SPARKLINE_INSET = 4
