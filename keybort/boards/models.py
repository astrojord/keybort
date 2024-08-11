from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
from django.db.models.constraints import CheckConstraint
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from . import const

class BoardsPermissions(models.Model):
    class Meta:
        permissions = (
            ('can_upload_stock_data', 'Can bulk upload stock data'),
            ('can_delete_stock_data', 'Can delete stock data'),
        )

# elected to not use generic FK/ContentType due to schema nastiness
# see great post @ https://lukeplant.me.uk/blog/posts/avoid-django-genericforeignkey/
# using nullable FKs in intermediate tables + props on each polymorphic model 

class Inventory(models.Model):
    """
    collects the Keyboards/Kits/Plates/Switches/Stabilizers/Keycaps for a user
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    keyboard = models.ForeignKey('Keyboard', null=True, blank=True, on_delete=models.SET_NULL)
    kit = models.ForeignKey('Kit', null=True, blank=True, on_delete=models.SET_NULL)
    plate = models.ForeignKey('Plate', null=True, blank=True, on_delete=models.SET_NULL)
    switch = models.ForeignKey('Switch', null=True, blank=True, on_delete=models.SET_NULL)
    stabilizer = models.ForeignKey('Stabilizer', null=True, blank=True, on_delete=models.SET_NULL)
    keycaps = models.ForeignKey('Keycaps', null=True, blank=True, on_delete=models.SET_NULL)
    
    @property
    def obj(self):
        if self.keyboard:
            return self.keyboard.obj
        elif self.kit:
            return self.kit.obj
        elif self.plate:
            return self.plate.obj
        elif self.switch:
            return self.switch.obj
        elif self.stabilizer:
            return self.switch.obj
        elif self.keycaps:
            return self.keycaps.obj
        
        raise AssertionError(f'missing data for inventory {self.pk}')   

    def __str__(self):
        return f'{self.user.username} - {self.obj}'

    class Meta:
        verbose_name_plural = 'Inventories'

        # todo: surely there's a better way to do this w/ some sort of boolean logic magic
        constraints = [
            CheckConstraint(check=(
                Q(keyboard__isnull=True) ^
                Q(kit__isnull=True) ^
                Q(plate__isnull=True) ^
                Q(switch__isnull=True) ^
                Q(stabilizer__isnull=True) ^
                Q(keycaps__isnull=True) 
            ), name='inventory_data_exists')
        ]

class Keyboard(models.Model):
    """
    collects a set of pieces that represent a built/planned board
    """
    custom = models.OneToOneField('CustomKeyboard', null=True, blank=True, on_delete=models.CASCADE, related_name='%(class)s_custom_obj')
    stock = models.OneToOneField('StockKeyboard', null=True, blank=True, on_delete=models.CASCADE, related_name='%(class)s_stock_obj')

    @property
    def obj(self):
        if self.custom:
            return self.custom
        elif self.stock:
            return self.stock
        
        raise AssertionError(f'missing data for keyboard {self.pk}')
    
    def __str__(self):
        obj = self.obj
        if obj.stock:
            return f'{obj} (stock)'
        else:
            return f'{obj} (custom)'
    
    class Meta:
        constraints = [
            CheckConstraint(check=Q(custom__isnull=True) ^ Q(stock__isnull=True), name='keyboard_data_exists')
        ]

class CustomKeyboard(models.Model):
    # can go to CustomKit or StockKit
    kit = models.ForeignKey('Kit', null=True, blank=True, on_delete=models.SET_NULL)

    # can go to CustomPlate or StockPlate
    plate = models.ForeignKey('Plate', null=True, blank=True, on_delete=models.SET_NULL)

    # can go to CustomSwitch or StockSwitch
    switch = models.ForeignKey('Switch', null=True, blank=True, on_delete=models.SET_NULL)

    # can go to CustomStabilizer or StockStabilizer
    stabilizer = models.ForeignKey('Stabilizer', null=True, blank=True, on_delete=models.SET_NULL)
    
    # can go to CustomKeycaps or StockPlate
    keycaps = models.ForeignKey('Keycaps', null=True, blank=True, on_delete=models.SET_NULL)

    bluetooth = models.BooleanField(default=False)
    wireless = models.BooleanField(default=False)

    notes = models.TextField(blank=True, null=True)
    references = models.TextField(blank=True, null=True, help_text='Documentation, QMK info, etc.')

    @property
    def stock(self):
        return False

    def __str__(self):
        return f'{self.kit.obj.brand} {self.kit.obj.name}'
    
class StockKeyboard(models.Model):
    kit = models.ForeignKey('StockKit', null=True, blank=True, on_delete=models.SET_NULL)
    plate = models.ForeignKey('StockPlate', null=True, blank=True, on_delete=models.SET_NULL)
    switch = models.ForeignKey('StockSwitch', null=True, blank=True, on_delete=models.SET_NULL)
    stabilizer = models.ForeignKey('StockStabilizer', null=True, blank=True, on_delete=models.SET_NULL)
    keycaps = models.ForeignKey('StockKeycaps', null=True, blank=True, on_delete=models.SET_NULL)

    bluetooth = models.BooleanField(default=False)
    wireless = models.BooleanField(default=False)

    notes = models.TextField(blank=True, null=True)
    references = models.TextField(blank=True, null=True, help_text='Documentation, QMK info, etc.')

    @property
    def stock(self):
        return True

    def __str__(self):
        return f'{self.kit.brand} {self.kit.name}'

class Kit(models.Model):
    custom = models.OneToOneField('CustomKit', null=True, blank=True, on_delete=models.CASCADE, related_name='%(class)s_custom_obj')
    stock = models.OneToOneField('StockKit', null=True, blank=True, on_delete=models.CASCADE, related_name='%(class)s_stock_obj')

    @property
    def obj(self):
        if self.custom:
            return self.custom
        elif self.stock:
            return self.stock
        
        raise AssertionError(f'missing data for kit {self.pk}')
    
    def __str__(self):
        obj = self.obj
        if obj.stock:
            return f'{obj} (stock)'
        else:
            return f'{obj} (custom)'
    
    class Meta:
        constraints = [
            CheckConstraint(check=Q(custom__isnull=True) ^ Q(stock__isnull=True), name='kit_data_exists')
        ]

# todo: there's probably a better thing to call this
class CustomKit(models.Model):
    brand = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    size = models.CharField(max_length=32, blank=True, null=True)
    total_keys = models.PositiveIntegerField(blank=True, null=True)
    pcb = models.CharField(max_length=255, blank=True, null=True)
    layout = models.CharField(max_length=255, blank=True, null=True, help_text='Refers to physical layout, not the individual caps placed on each switch (e.g. Dvorak, QZERTY).')
    case_material = models.CharField(max_length=255, blank=True, null=True)
    mount_type = models.CharField(max_length=255, blank=True, null=True)

    notes = models.TextField(blank=True, null=True)

    @property
    def stock(self):
        return False
    
    def __str__(self):
        return f'{self.brand} {self.name} (kit)'
    
class StockKit(CustomKit):
    """
    preconfigured kit to be selected by users instead of typing custom attributes
    """

    @property
    def stock(self):
        return True
    
    def __str__(self):
        return f'{self.brand} {self.name} (kit)'

class Plate(models.Model):
    custom = models.OneToOneField('CustomPlate', null=True, blank=True, on_delete=models.CASCADE, related_name='%(class)s_custom_obj')
    stock = models.OneToOneField('StockPlate', null=True, blank=True, on_delete=models.CASCADE, related_name='%(class)s_stock_obj')

    @property
    def obj(self):
        if self.custom:
            return self.custom
        elif self.stock:
            return self.stock
        
        raise AssertionError(f'missing data for plate {self.pk}')
    
    def __str__(self):
        obj = self.obj
        if obj.stock:
            return f'{obj} (stock)'
        else:
            return f'{obj} (custom)'
    
    class Meta:
        constraints = [
            CheckConstraint(check=Q(custom__isnull=True) ^ Q(stock__isnull=True), name='plate_data_exists')
        ]

class CustomPlate(models.Model):
    material = models.CharField(max_length=255, blank=True, null=True)
    flex_cuts = models.BooleanField(default=False)
    half = models.BooleanField(default=False)

    notes = models.TextField(blank=True, null=True)

    @property
    def stock(self):
        return False

    def __str__(self):
        s = self.material
        if self.flex_cuts:
            s += ' (flex)'
        if self.half:
            s += ' (half)'

        return s

class StockPlate(CustomPlate):
    """
    preconfigured plate to be selected by users instead of typing custom attributes
    """
    @property
    def stock(self):
        return True
    
    def __str__(self):
        s = self.material
        if self.flex_cuts:
            s += ' (flex)'
        if self.half:
            s += ' (half)'

        return s

class Switch(models.Model):
    custom = models.OneToOneField('CustomSwitch', null=True, blank=True, on_delete=models.CASCADE, related_name='%(class)s_custom_obj')
    stock = models.OneToOneField('StockSwitch', null=True, blank=True, on_delete=models.CASCADE, related_name='%(class)s_stock_obj')

    @property
    def obj(self):
        if self.custom:
            return self.custom
        elif self.stock:
            return self.stock
        
        raise AssertionError(f'missing data for switch {self.pk}')
    
    def __str__(self):
        obj = self.obj
        if obj.stock:
            return f'{obj} (stock)'
        else:
            return f'{obj} (custom)'
    
    class Meta:
        verbose_name_plural = 'Switches'
        constraints = [
            CheckConstraint(check=Q(custom__isnull=True) ^ Q(stock__isnull=True), name='switch_data_exists')
        ]

class CustomSwitch(models.Model):
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

    @property
    def stock(self):
        return False

    def __str__(self):
        return f'{self.brand} {self.name} ({self.get_category_display()}, {self.bottom_out_force}g)'
    
    class Meta:
        verbose_name_plural = 'Custom switches'

class StockSwitch(CustomSwitch):
    """
    preconfigured switch to be selected by users instead of typing custom attributes
    """

    @property
    def stock(self):
        return True
    
    def __str__(self):
        return f'{self.brand} {self.name} ({self.get_category_display()}, {self.bottom_out_force}g)'
    
    class Meta:
        verbose_name_plural = 'Stock switches'

class Stabilizer(models.Model):
    custom = models.OneToOneField('CustomStabilizer', null=True, blank=True, on_delete=models.CASCADE, related_name='%(class)s_custom_obj')
    stock = models.OneToOneField('StockStabilizer', null=True, blank=True, on_delete=models.CASCADE, related_name='%(class)s_stock_obj')

    @property
    def obj(self):
        if self.custom:
            return self.custom
        elif self.stock:
            return self.stock
        
        raise AssertionError(f'missing data for stabilizer {self.pk}')
    
    def __str__(self):
        obj = self.obj
        if obj.stock:
            return f'{obj} (stock)'
        else:
            return f'{obj} (custom)'
    
    class Meta:
        constraints = [
            CheckConstraint(check=Q(custom__isnull=True) ^ Q(stock__isnull=True), name='stabilizer_data_exists')
        ]

class CustomStabilizer(models.Model):
    brand = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)

    notes = models.TextField(blank=True, null=True)

    @property
    def stock(self):
        return False

    def __str__(self):
        return f'{self.brand} {self.name}'
    
class StockStabilizer(CustomStabilizer):
    """
    preconfigured stabilizer to be selected by users instead of typing custom attributes
    """

    @property
    def stock(self):
        return True
    
    def __str__(self):
        return f'{self.brand} {self.name}'

class Keycaps(models.Model):
    custom = models.OneToOneField('CustomKeycaps', null=True, blank=True, on_delete=models.CASCADE, related_name='%(class)s_custom_obj')
    stock = models.OneToOneField('StockKeycaps', null=True, blank=True, on_delete=models.CASCADE, related_name='%(class)s_stock_obj')

    @property
    def obj(self):
        if self.custom:
            return self.custom
        elif self.stock:
            return self.stock
        
        raise AssertionError(f'missing data for keycaps {self.pk}')
    
    def __str__(self):
        obj = self.obj
        if obj.stock:
            return f'{obj} (stock)'
        else:
            return f'{obj} (custom)'
    
    class Meta:
        verbose_name_plural = verbose_name = 'Keycaps'
        constraints = [
            CheckConstraint(check=Q(custom__isnull=True) ^ Q(stock__isnull=True), name='keycaps_data_exists')
        ]

class CustomKeycaps(models.Model):
    brand = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    material = models.CharField(max_length=255, blank=True, null=True)

    notes = models.TextField(blank=True, null=True)

    @property
    def stock(self):
        return False

    def __str__(self):
        return f'{self.brand} {self.name}'
    
    class Meta:
        verbose_name_plural = verbose_name = 'Custom keycaps'

class StockKeycaps(CustomKeycaps):
    """
    preconfigured kit to be selected by users instead of typing custom attributes
    """

    @property
    def stock(self):
        return True
    
    def __str__(self):
        return f'{self.brand} {self.name}'
    
    class Meta:
        verbose_name_plural = verbose_name = 'Stock keycaps'

# todo: artisans + breaking down for mixed sets (like alphas from one, mods from another or gmk base + highlight)
class Mod(models.Model):
    custom = models.OneToOneField('CustomMod', null=True, blank=True, on_delete=models.CASCADE, related_name='%(class)s_custom_obj')
    stock = models.OneToOneField('StockMod', null=True, blank=True, on_delete=models.CASCADE, related_name='%(class)s_stock_obj')

    @property
    def obj(self):
        if self.custom:
            return self.custom
        elif self.stock:
            return self.stock
        
        raise AssertionError(f'missing data for mod {self.pk}')
    
    def __str__(self):
        obj = self.obj
        if obj.stock:
            return f'{obj} (stock)'
        else:
            return f'{obj} (custom)'
    
    class Meta:
        constraints = [
            CheckConstraint(check=Q(custom__isnull=True) ^ Q(stock__isnull=True), name='mod_data_exists')
        ]

class CustomMod(models.Model):
    """
    represents foams, lube/film, tape mod, etc.
    """
    # can go to CustomKit or StockKit
    kit = models.ForeignKey('Kit', null=True, blank=True, on_delete=models.SET_NULL)

    # can go to CustomPlate or StockPlate
    plate = models.ForeignKey('Plate', null=True, blank=True, on_delete=models.SET_NULL)

    # can go to CustomSwitch or StockSwitch
    switch = models.ForeignKey('Switch', null=True, blank=True, on_delete=models.SET_NULL)

    # can go to CustomStabilizer or StockStabilizer
    stabilizer = models.ForeignKey('Stabilizer', null=True, blank=True, on_delete=models.SET_NULL)
    
    # can go to CustomKeycaps or StockPlate
    keycaps = models.ForeignKey('Keycaps', null=True, blank=True, on_delete=models.SET_NULL)

    mod = models.TextField()
    notes = models.TextField(blank=True, null=True)

    @property
    def obj(self):
        if self.kit:
            return self.kit.obj
        elif self.plate:
            return self.plate.obj
        elif self.switch:
            return self.switch.obj
        elif self.stabilizer:
            return self.switch.obj
        elif self.keycaps:
            return self.keycaps.obj
        
        raise AssertionError(f'missing data for mod {self.pk}')
    
    @property
    def stock(self):
        return False

    class Meta:
        # todo: surely there's a better way to do this w/ some sort of boolean logic magic
        constraints = [
            CheckConstraint(check=(
                Q(kit__isnull=True) ^
                Q(plate__isnull=True) ^
                Q(switch__isnull=True) ^
                Q(stabilizer__isnull=True) ^
                Q(keycaps__isnull=True) 
            ), name='%(class)s_obj_data_exists')
        ]

class StockMod(CustomMod):
    """
    preconfigured mod to be selected by users instead of typing custom attributes
    """
    
    @property
    def stock(self):
        return True