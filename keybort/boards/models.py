from django.contrib.auth.models import User
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from . import const

class BoardsPermissions(models.Model):
    class Meta:
        permissions = (
            ('can_upload_canned_data', 'Can bulk upload canned data'),
            ('can_delete_canned_data', 'Can delete canned data'),
        )

class Inventory(models.Model):
    """
    collects the Keyboards/Kits/Plates/Switches/Stabilizers/Keycaps for a user
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return f'{self.user.username} - {self.content_type} {self.object_id}'

    class Meta:
        verbose_name_plural = 'Inventories'

class Keyboard(models.Model):
    """
    collects a set of pieces that represent a built/planned board
    """
    # can go to Kit or CannedKit
    kit_limit = models.Q(app_label='boards', model='kit') | models.Q(app_label='boards', model='cannedkit')
    kit_content_type = models.ForeignKey(ContentType, limit_choices_to=kit_limit, on_delete=models.CASCADE, related_name='board_kit')
    kit_object_id = models.PositiveIntegerField()
    kit_content_object = GenericForeignKey('kit_content_type', 'kit_object_id')

    # can go to Plate or CannedPlate
    plate_limit = models.Q(app_label='boards', model='plate') | models.Q(app_label='boards', model='cannedplate')
    plate_content_type = models.ForeignKey(ContentType, limit_choices_to=plate_limit, null=True, on_delete=models.SET_NULL, related_name='board_plate')
    plate_object_id = models.PositiveIntegerField(null=True)
    plate_content_object = GenericForeignKey('plate_content_type', 'plate_object_id')

    # can go to Switch or CannedSwitch
    switch_limit = models.Q(app_label='boards', model='switch') | models.Q(app_label='boards', model='cannedswitch')
    switch_content_type = models.ForeignKey(ContentType, limit_choices_to=switch_limit, null=True, on_delete=models.SET_NULL, related_name='board_switch')
    switch_object_id = models.PositiveIntegerField(null=True)
    switch_content_object = GenericForeignKey('switch_content_type', 'switch_object_id')

    # can go to Stabilizer or CannedStabilizer
    stabilizer_limit = models.Q(app_label='boards', model='stabilizer') | models.Q(app_label='boards', model='cannedstabilizer')
    stabilizer_content_type = models.ForeignKey(ContentType, limit_choices_to=stabilizer_limit, null=True, on_delete=models.SET_NULL, related_name='board_stabilizer')
    stabilizer_object_id = models.PositiveIntegerField(null=True)
    stabilizer_content_object = GenericForeignKey('stabilizer_content_type', 'stabilizer_object_id')
    
    # can go to Keycaps or CannedKeycaps
    keycaps_limit = models.Q(app_label='boards', model='keycaps') | models.Q(app_label='boards', model='cannedkeycaps')
    keycaps_content_type = models.ForeignKey(ContentType, limit_choices_to=keycaps_limit, null=True, on_delete=models.SET_NULL, related_name='board_keycaps')
    keycaps_object_id = models.PositiveIntegerField(null=True)
    keycaps_content_object = GenericForeignKey('keycaps_content_type', 'keycaps_object_id')

    prebuilt = models.BooleanField(default=False)
    bluetooth = models.BooleanField(default=False)
    wireless = models.BooleanField(default=False)

    notes = models.TextField(blank=True, null=True)
    references = models.TextField(blank=True, null=True, help_text='Documentation, QMK info, etc.')

    def __str__(self):
        return f'{self.kit_content_object.brand} {self.kit_content_object.name}'

# todo: there's probably a better thing to call this
class Kit(models.Model):
    brand = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    size = models.CharField(max_length=32, blank=True, null=True)
    total_keys = models.PositiveIntegerField(blank=True, null=True)
    pcb = models.CharField(max_length=255, blank=True, null=True)
    layout = models.CharField(max_length=255, blank=True, null=True, help_text='Refers to physical layout, not the individual caps placed on each switch (e.g. Dvorak, QZERTY).')
    case_material = models.CharField(max_length=255, blank=True, null=True)
    mount_type = models.CharField(max_length=255, blank=True, null=True)

    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'{self.brand} {self.name} (kit)'

class Plate(models.Model):
    material = models.CharField(max_length=255, blank=True, null=True)
    flex_cuts = models.BooleanField(default=False)
    half = models.BooleanField(default=False)

    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        s = self.material
        if self.flex_cuts:
            s += ' (flex)'
        if self.half:
            s += ' (half)'

        return s

class Switch(models.Model):
    quantity = models.PositiveIntegerField(blank=True, null=True)
    brand = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    category = models.CharField(max_length=255, blank=True, null=True, choices=const.SWITCH_CATEGORIES)
    stem = models.CharField(max_length=255, blank=True, null=True, default='mx', choices=const.SWITCH_STEMS)
    peak_force = models.FloatField(blank=True, null=True, help_text='gf')
    bottom_out_force = models.FloatField(blank=True, null=True, help_text='gf')
    travel_distance = models.FloatField(blank=True, null=True, help_text='mm')
    top_housing = models.CharField(max_length=255, blank=True, null=True, choices=const.SWITCH_MATERIALS)
    bottom_housing = models.CharField(max_length=255, blank=True, null=True, choices=const.SWITCH_MATERIALS)

    lubed = models.BooleanField(default=False)
    filmed = models.BooleanField(default=False)

    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'{self.brand} {self.name} ({self.get_category_display()}, {self.bottom_out_force}g)'
    
    class Meta:
        verbose_name_plural = 'Switches'

class Stabilizer(models.Model):
    brand = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)

    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'{self.brand} {self.name}'

class Keycaps(models.Model):
    brand = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    material = models.CharField(max_length=255, blank=True, null=True)

    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'{self.brand} {self.name}'
    
    class Meta:
        verbose_name_plural = verbose_name = 'Keycaps'

# todo: artisans + breaking down for mixed sets (like alphas from one, mods from another or gmk base + highlight)

class Mod(models.Model):
    """
    represents foams, lube/film, tape mod, etc.
    """
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    mod = models.TextField()
    notes = models.TextField(blank=True, null=True)

class CannedKit(Kit):
    """
    preconfigured kit to be selected by users instead of typing custom attributes
    """
    def __str__(self):
        return f'{self.brand} {self.name} (kit)'

class CannedPlate(Plate):
    """
    preconfigured plate to be selected by users instead of typing custom attributes
    """
    def __str__(self):
        s = self.material
        if self.flex_cuts:
            s += ' (flex)'
        if self.half:
            s += ' (half)'

        return s

class CannedSwitch(Switch):
    """
    preconfigured switch to be selected by users instead of typing custom attributes
    """
    def __str__(self):
        return f'{self.brand} {self.name} ({self.get_category_display()}, {self.bottom_out_force}g)'
    
    class Meta:
        verbose_name_plural = 'Canned switches'

class CannedStabilizer(Stabilizer):
    """
    preconfigured stabilizer to be selected by users instead of typing custom attributes
    """
    def __str__(self):
        return f'{self.brand} {self.name}'

class CannedKeycaps(Keycaps):
    """
    preconfigured kit to be selected by users instead of typing custom attributes
    """
    def __str__(self):
        return f'{self.brand} {self.name}'
    
    class Meta:
        verbose_name_plural = verbose_name = 'Canned keycaps'

class CannedMod(Mod):
    """
    preconfigured mod to be selected by users instead of typing custom attributes
    """
    pass