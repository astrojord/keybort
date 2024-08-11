from django.contrib import admin

from . import models

admin.site.register([
    models.Inventory, models.Keyboard, 
    models.Kit, models.Plate, models.Switch,
    models.Stabilizer, models.Keycaps, models.Mod,
    models.CustomKeyboard, 
    models.CustomKit, models.CustomPlate, models.CustomSwitch, 
    models.CustomStabilizer, models.CustomKeycaps, models.CustomMod,
    models.StockKeyboard,
    models.StockKit, models.StockPlate, models.StockSwitch, 
    models.StockStabilizer, models.StockKeycaps, models.StockMod,
])