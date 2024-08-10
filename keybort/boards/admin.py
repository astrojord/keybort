from django.contrib import admin

from . import models

admin.site.register([
    models.Inventory, models.Keyboard, 
    models.Kit, models.Plate, models.Switch, models.Stabilizer, models.Keycaps, models.Mod
])