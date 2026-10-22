LAYOUTS = [
    ('ansi', 'ANSI'),
    ('hhkb', 'HHKB'),
    ('iso', 'ISO'),
    ('qaz', 'QAZ'),
    ('wkl', 'WKL'),
]

CASE_MATERIALS = [
    ('abs', 'ABS'),
    ('acr', 'Acrylic'),
    ('alu', 'Aluminum'),
    ('ano_alu', 'Aluminum (anodized)'),
    ('ck_alu', 'Aluminum (cerakoted)'),
    ('ec_alu', 'Aluminum (e-coated)'),
    ('fr4_stack', 'FR4 Stack'),
    ('p', 'Plastic'),
    ('pc', 'Polycarbonate'),
    ('w', 'Wood'),
    ('tdp', '3DP'),
]

MOUNT_TYPES = [
    ('bottom', 'Bottom'),
    ('gasket', 'Gasket'),
    ('ip', 'Integrated Plate'),
    ('iso', 'Isolation'),
    ('isotop', 'Isolated Top'),
    ('pl', 'Plateless'),
    ('sandwich', 'Sandwich'),
    ('top', 'Top'),
    ('tray', 'Tray'),
]

PLATE_MATERIALS = [
    ('alu', 'Aluminum'),
    ('b', 'Brass'),
    ('cf', 'Carbon Fiber'),
    ('fr4', 'FR4'),
    ('pc', 'Polycarbonate'),
    ('pom', 'POM'),
    ('ss', 'Stainless Steel'),
    ('tdp', '3DP'),
]

PCB_TYPES = [
    ('hs', 'Hotswap'),
    ('s', 'Solder'),
    ('mm', 'Millmaxed'),
]

SWITCH_CATEGORIES = [
    ('l', 'Linear'),
    ('sl', 'Silent Linear'),
    ('t', 'Tactile'),
    ('st', 'Silent Tactile'),
    ('c', 'Clicky'),
]

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

KEYCAP_MATERIALS = [
    ('abs', 'ABS'),
    ('abs_ds', 'ABS (Doubleshot)'),
    ('alu', 'Aluminum'),
    ('pbt', 'PBT'),
    ('pom', 'POM'),
    ('tdp', '3DP'),
    ('w', 'Wood'),
]
# part types in display order. the model/form behind each one lives on KeyboardManager.PART_MODELS,
# since models.py imports this file
PART_SINGULARS = {
    'kit': 'Kit',
    'switch': 'Switch',
    'keycaps': 'Keycaps',
    'plate': 'Plate',
    'stabilizer': 'Stabilizer',
}

PART_PLURALS = {
    'kit': 'Kits',
    'switch': 'Switches',
    'keycaps': 'Keycaps',
    'plate': 'Plates',
    'stabilizer': 'Stabilizers',
}

# tabs on the keyboards page, keyed by the row's data-type
KEYBOARD_KINDS = {
    'prebuilt': 'Prebuilts',
    'custom': 'Customs',
}

# headings for each part's step in the keyboard/part modals
PART_STEP_LABELS = {
    'kit': 'Kit',
    'switch': 'Switches',
    'keycaps': 'Keycaps',
    'plate': 'Plate',
    'stabilizer': 'Stabilizers',
}

# htmx event the page dialogs listen for to close themselves after a save
CLOSE_DIALOG_EVENT = 'close-dialog'

QUANTITY_ERROR = 'Enter a whole number, 1 or more.'

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

PART_SOURCE_DEFAULTS = {
    'smart': (
        'Smart',
        'Prefer parts in inventory first, then stock.',
    ),
    'stock': ('Stock', 'Pick from the catalog.'),
    'custom': ('Custom', 'Enter the details yourself.'),
}
