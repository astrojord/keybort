from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test

from .forms import (
    KitForm, KeycapsForm, SwitchForm, StabilizerForm, PlateForm, ModForm
)
from .handlers import handle_canned_parts_upload
from .models import (
    Inventory, Keyboard, 
    Kit, Keycaps, Switch, Stabilizer, Plate, Mod, 
    CannedKit, CannedKeycaps, CannedSwitch, CannedStabilizer, CannedPlate, CannedMod
)

# home/dashboard
def index(request):
    context = {'page_title': 'Home'}
    return render(request, 'pages/index.html', context)

# keyboard inventory
@login_required(login_url='/accounts/login')
def inventory_keyboards(request):
    pass

# parts inventory

# add/change keyboard in inventory

# add/change individual parts in inventory
# 1 view for each form to handle xhr post request: Kit, Keycaps, Switch, Stabilizer, Plate, Mod

# unified search for canned parts

# 1 view for each list of canned parts: Kit, Keycaps, Switch, Stabilizer, Plate, Mod

# upload canned parts (needs permission)

