from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404

from .forms import (
    KitForm, KeycapsForm, SwitchForm, StabilizerForm, PlateForm, ModForm
)
from .handlers import handle_canned_parts_upload
from .models import (
    Inventory, CustomKeyboard, StockKeyboard,
    CustomKit, CustomKeycaps, CustomSwitch, CustomStabilizer, CustomPlate, CustomMod,
    StockKit, StockKeycaps, StockSwitch, StockStabilizer, StockPlate, StockMod
)
from .utils import model_to_dict_verbose

# home/dashboard
def index(request):
    context = {'page_title': 'Home'}
    return render(request, 'pages/index.html', context)

@login_required(login_url='/accounts/login')
def inventory_keyboards(request):
    context = {'page_title': 'Keyboard Inventory'}

    # each instance here will be either CustomKeyboard or StockKeyboard
    user_inventory_qs = [
        i.obj for i in 
        Inventory.objects
            .filter(user=request.user)
            .exclude(keyboard__isnull=True)
            .prefetch_related(
                'kit', 'keycaps', 'switch',
                'plate', 'stabilizer',
            )
    ]
    
    inventory = []
    for kb in user_inventory_qs:
        data = {
            'id': kb.pk,
            'url_params': f'id={kb.pk}&stock={int(kb.stock)}',
            'stock': kb.stock,
            'notes': kb.notes,
        }

        if kb.kit:
            data.update({
                'kit_url_params': f'type=kit&id={kb.kit.obj.pk}&stock={int(kb.kit.obj.stock)}',
                'kit_str': f'{kb.kit.obj.brand} {kb.kit.obj.name}',
                'pcb': kb.kit.obj.pcb,
            })
        
        if kb.switch:
            data.update({
                'switches_url_params': f'type=switch&id={kb.switch.obj.pk}&stock={int(kb.switch.obj.stock)}',
                'switches_str': f'{kb.switch.obj.brand} {kb.switch.obj.name}',
            })

        if kb.keycaps:
            data.update({
                'keycaps_url_params': f'type=keycaps&id={kb.keycaps.obj.pk}&stock={int(kb.keycaps.obj.stock)}',
                'keycaps_str': str(kb.keycaps.obj),
            })

        if kb.plate:
            data.update({
                'plate_url_params': f'type=plate&id={kb.plate.obj.pk}&stock={int(kb.plate.obj.stock)}',
                'plate_str': str(kb.plate.obj),
            })

        if kb.stabilizer:
            data.update({
                'stabilizer_url_params': f'type=stabilizer&id={kb.stabilizer.obj.pk}&stock={int(kb.stabilizer.obj.stock)}',
                'stabilizer_str': str(kb.stabilizer.obj),
            })
                
        inventory.append(data)

    context['inventory'] = inventory
    # cut off text for part names after maybe 50 characters?
    # cut off text for mods + notes after some longer amount of characters
    return render(request, 'pages/inventory_keyboards.html', context)

@login_required(login_url='/accounts/login')
def inventory_parts(request):
    context = {'page_title': 'Parts Inventory'}

    user_inventory = [i.obj for i in Inventory.objects.filter(user=request.user, keyboard__isnull=True)]

    return render(request, 'pages/inventory_parts.html', context)

# returns view-only modal body on HTMX request from either inventory page 
def part_detail(request):
    part_type = request.GET.get('type')
    part_id = request.GET.get('id')
    stock = bool(int(request.GET.get('stock')))

    if any([x is None for x in [part_type, part_id, stock]]):
        return HttpResponse(status=400)
    
    context = {}

    # would love to use model_to_dict here but need user-readable dict keys
    # todo: make own model_to_dist that returns verbose names as keys
    match part_type:
        case 'kit':
            if stock:
                obj = get_object_or_404(StockKit, pk=part_id)
            else:
                obj = get_object_or_404(CustomKit, pk=part_id)

        case 'switch':
            if stock:
                obj = get_object_or_404(StockSwitch, pk=part_id)
            else:
                obj = get_object_or_404(CustomSwitch, pk=part_id)

        case 'keycaps':
            if stock:
                obj = get_object_or_404(StockKeycaps, pk=part_id)
            else:
                obj = get_object_or_404(CustomKeycaps, pk=part_id)

        case 'plate':
            if stock:
                obj = get_object_or_404(StockPlate, pk=part_id)
            else:
                obj = get_object_or_404(CustomPlate, pk=part_id)

        case 'stabilizer':
            if stock:
                obj = get_object_or_404(StockStabilizer, pk=part_id)
            else:
                obj = get_object_or_404(CustomStabilizer, pk=part_id)

        case _:
            return HttpResponse(status=400)

    context['part_title'] = str(obj)
    context['fields'] = model_to_dict_verbose(obj, exclude=['id', f'custom{part_type}_ptr', f'stock{part_type}_ptr', 'quantity'])
    
    return render(request, f'partials/detail_modal.html', context)

@login_required(login_url='/accounts/login')
def keyboard_detail(request):
    kb_id = request.GET.get('id')
    stock = bool(int(request.GET.get('stock')))
    # include change forms for each component
    # include delete button (modal for confirm)
    pass

@login_required(login_url='/accounts/login')
def add_keyboard(request):
    # redirect to detail page for created board after form validation
    pass

@login_required(login_url='/accounts/login')
def delete_keyboard(request):
    kb_id = request.GET.get('id')
    stock = bool(int(request.GET.get('stock')))

    # validate inventory user == request user or 403
    if stock:
        obj = get_object_or_404(StockKeyboard, pk=kb_id)
        try:
            inv_obj = Inventory.objects.get(user=request.user, keyboard__stock=obj)
        except Inventory.DoesNotExist:
            return HttpResponse(status=403)
    else:
        obj = get_object_or_404(CustomKeyboard, pk=kb_id)
        try:
            inv_obj = Inventory.objects.get(user=request.user, keyboard__custom=obj)
        except Inventory.DoesNotExist:
            return HttpResponse(status=403)
        
    inv_obj.delete()
    return HttpResponse(status=200)

# add/change individual parts in inventory
# 1 view for each form to handle xhr post request from keyboard_detail
# Kit, Keycaps, Switch, Stabilizer, Plate, Mod

# unified search for stock parts
def search_stock(request):
    pass

# 1 view for each list of stock parts: Keyboard, Kit, Keycaps, Switch, Stabilizer, Plate
def stock_prebuilts(request):
    context = {'page_title': 'Prebuilt Keyboards'}
    return render(request, 'pages/stock_prebuilts.html', context)

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

