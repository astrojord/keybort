from django.contrib.auth.models import User
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from . import const

class Inventory(models.Model):
    """
    collects the Keyboards/Kits/Plates/Switches/Stabilizers/Keycaps for a user
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

class Keyboard(models.Model):
    """
    collects a set of pieces that represent a built/planned board
    """
    kit = models.ForeignKey('Kit', null=True, on_delete=models.SET_NULL)
    plate = models.ForeignKey('Plate', null=True, on_delete=models.SET_NULL)
    switch = models.ForeignKey('Switch', null=True, on_delete=models.SET_NULL)
    stabilizer = models.ForeignKey('Stabilizer', null=True, on_delete=models.SET_NULL)
    keycaps = models.ForeignKey('Keycaps', null=True, on_delete=models.SET_NULL)

    prebuilt = models.BooleanField(default=False)
    bluetooth = models.BooleanField(default=False)
    wireless = models.BooleanField(default=False)

    notes = models.TextField(blank=True, null=True)
    references = models.TextField(blank=True, null=True, help_text='Documentation, QMK info, etc.')

# todo: there's probably a better thing to call this
class Kit(models.Model):
    brand = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    size = models.CharField(max_length=32, blank=True, null=True)
    total_keys = models.PositiveIntegerField(blank=True, null=True)
    pcb = models.CharField(max_length=255, blank=True, null=True)
    layout = models.CharField(max_length=255, blank=True, null=True, help_text='Refers to physical layout, not the individual caps placed on each switch (i.e. Dvorak, QZERTY).')
    case_material = models.CharField(max_length=255, blank=True, null=True)
    mount_type = models.CharField(max_length=255, blank=True, null=True)

    notes = models.TextField(blank=True, null=True)

class Plate(models.Model):
    material = models.CharField(max_length=255, blank=True, null=True)
    flex_cuts = models.BooleanField(default=False)
    half = models.BooleanField(default=False)

    notes = models.TextField(blank=True, null=True)

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

class Stabilizer(models.Model):
    brand = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)

    notes = models.TextField(blank=True, null=True)

class Keycaps(models.Model):
    brand = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    material = models.CharField(max_length=255, blank=True, null=True)

    notes = models.TextField(blank=True, null=True)

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
