from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.shortcuts import render

from .forms import (
    KitForm, KeycapsForm, SwitchForm, StabilizerForm, PlateForm, ModForm
)
from .handlers import handle_canned_parts_upload
from .models import (
    Inventory, Keyboard,
    Kit, Keycaps, Switch, Stabilizer, Plate, Mod
)

# home/dashboard
def index(request):
    context = {'page_title': 'Home'}
    return render(request, 'pages/index.html', context)

@login_required(login_url='/accounts/login')
def inventory_keyboards(request):
    context = {'page_title': 'Keyboard Inventory'}

    user_inventory = Inventory.objects.filter(user=request.user)
    # cut off text for part names after maybe 50 characters?
    # cut off text for mods + notes after some longer amount of characters
    return render(request, 'pages/inventory_keyboards.html', context)

@login_required(login_url='/accounts/login')
def inventory_parts(request):
    context = {'page_title': 'Parts Inventory'}
    return render(request, 'pages/inventory_parts.html', context)

# returns view-only modal body on HTMX request from either inventory page 
def part_detail(request):
    part_type = request.GET.get('type')
    part_id = request.GET.get('id')
    canned = bool(request.GET.get('stock'))

    if all([x is not None for x in [part_type, part_id, canned]]):
        return HttpResponse(status=400)

    # todo: 
    # retrieve part by type and ID, making query to diff model depending on canned param
    # return 404 if invalid params

    # get data about part to display in modal
    context = {}
    
    return render(request, f'partials/{part_type}_modal.html', context)

@login_required(login_url='/accounts/login')
def keyboard_detail(request):
    # include change forms for each component
    # include delete button (modal for confirm)
    pass

@login_required(login_url='/accounts/login')
def add_keyboard(request):
    # redirect to detail page for created board after form validation
    pass

# add/change individual parts in inventory
# 1 view for each form to handle xhr post request from keyboard_detail
# Kit, Keycaps, Switch, Stabilizer, Plate, Mod

# unified search for canned parts
def search_canned(request):
    pass

# eventually:
# def stock_prebuilts(request):
#     pass

# 1 view for each list of canned parts: Kit, Keycaps, Switch, Stabilizer, Plate
def stock_kits(request):
    pass

def stock_keycaps(request):
    pass

def stock_switches(request):
    pass

def stock_stabilizers(request):
    pass

def stock_plates(request):
    pass

# upload canned parts (needs permission)

