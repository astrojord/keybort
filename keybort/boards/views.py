from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.urls import reverse

from . import const
from .forms import (
    KeycapsForm,
    KitForm,
    ModForm,
    PlateForm,
    ProfileForm,
    StabilizerForm,
    SwitchForm,
)
from .handlers import handle_canned_parts_upload
from .managers import KeyboardManager
from .utils import htmx_swap, keyboard_params, model_to_dict_verbose


def keyboard_name(row):
    return row.get('kit_str', 'keyboard')


# home/dashboard
def index(request):
    context = {'page_title': 'Home'}
    if request.user.is_authenticated:
        context.update(KeyboardManager(request.user).dashboard())
        context['quick_actions'] = const.QUICK_ACTIONS
    return render(request, 'pages/index.html', context)


@login_required(login_url='/accounts/login')
def inventory_keyboards(request):
    context = {'page_title': 'Keyboard Inventory'}
    context['inventory'] = KeyboardManager(request.user).keyboard_rows()
    context['filters'] = list(const.KEYBOARD_KINDS.items())
    add = request.GET.get('add')
    context['open_add'] = add if add in const.KEYBOARD_KINDS else None
    # cut off text for part names after maybe 50 characters?
    # cut off text for mods + notes after some longer amount of characters
    return render(request, 'pages/inventory_keyboards.html', context)


@login_required(login_url='/accounts/login')
def inventory_parts(request):
    context = {'page_title': 'Parts Inventory'}
    context['inventory'] = KeyboardManager(request.user).part_rows()
    context['filters'] = list(const.PART_PLURALS.items())
    add = request.GET.get('add')
    if add is not None:
        context['open_add'] = add if add in KeyboardManager.PART_MODELS else ''
    return render(request, 'pages/inventory_parts.html', context)


# GET: modal body, pick a part type then stock or custom
# POST: add it to the parts inventory, or bump quantity if exists
@login_required(login_url='/accounts/login')
def add_part(request):
    manager = KeyboardManager(request.user)
    if request.method != 'POST':
        part_type = request.GET.get('type')
        if part_type not in manager.PART_MODELS:
            part_type = None
        return render(
            request,
            'partials/part_add_modal.html',
            manager.add_part_context(part_type=part_type),
        )

    context = manager.add_part_context(request.POST)
    if context['part_type'] not in manager.PART_MODELS:
        return HttpResponse(status=400)

    result = manager.add_part(context, request.POST)
    if result is None:
        return render(request, 'partials/part_add_modal.html', context)

    inv, stacked = result
    row = manager.part_row(inv)
    if stacked:
        messages.success(
            request, f'Updated quantity of {row["name"]} to {inv.quantity}.'
        )
    else:
        messages.success(request, f'Added {row["name"]} to parts.')
    response = render(request, 'partials/part_row.html', {'part': row})
    if stacked:
        return htmx_swap(
            response, f'#part-{inv.pk}', 'outerHTML', const.CLOSE_DIALOG_EVENT
        )
    return htmx_swap(
        response, '#table-parts tbody', 'beforeend', const.CLOSE_DIALOG_EVENT
    )


@login_required(login_url='/accounts/login')
def edit_part(request):
    part_id = request.GET.get('id', '')
    if not part_id.isdigit():
        return HttpResponse(status=400)

    manager = KeyboardManager(request.user)
    inv = manager.standalone_part(part_id)
    if inv is None:
        messages.error(request, 'That part no longer exists.')
        raise Http404

    action_url = f'{reverse("part_edit")}?id={inv.pk}'
    if request.method != 'POST':
        return render(
            request,
            'partials/part_edit_modal.html',
            manager.edit_part_context(inv, action_url),
        )

    context = manager.edit_part_context(inv, action_url, request.POST)
    inv = manager.edit_part(context, request.POST)
    if inv is None:
        return render(request, 'partials/part_edit_modal.html', context)

    row = manager.part_row(inv)
    messages.success(request, f'Saved {row["name"]}.')
    response = render(request, 'partials/part_row.html', {'part': row})
    return htmx_swap(response, f'#part-{inv.pk}', 'outerHTML', const.CLOSE_DIALOG_EVENT)


# GET: confirmation modal
# POST: drop it from inventory
@login_required(login_url='/accounts/login')
def delete_part(request):
    part_id = request.GET.get('id', '')
    if not part_id.isdigit():
        return HttpResponse(status=400)

    manager = KeyboardManager(request.user)
    inv = manager.standalone_part(part_id)
    if inv is None:
        messages.error(request, 'That part no longer exists.')
        raise Http404

    if request.method != 'POST':
        context = manager.delete_part_context(
            inv, f'{reverse("part_delete")}?id={inv.pk}'
        )
        return render(request, 'partials/part_delete_modal.html', context)

    row = manager.part_row(inv)
    manager.delete_part(inv)
    messages.success(request, f'Removed {row["name"]} from parts.')
    row_id = row['row_id']
    return htmx_swap(HttpResponse(), f'#{row_id}', 'delete', const.CLOSE_DIALOG_EVENT)


# view-only modal body
def part_detail(request):
    part_type = request.GET.get('type')
    part_id = request.GET.get('id', '')
    stock = request.GET.get('stock')

    if (
        part_type not in KeyboardManager.PART_MODELS
        or not part_id.isdigit()
        or stock not in ('0', '1')
    ):
        return HttpResponse(status=400)

    # 404 for someone else's custom part too, so ids aren't confirmed
    obj = KeyboardManager(request.user).visible_part(part_type, part_id, stock == '1')
    if obj is None:
        raise Http404

    context = {
        'part_title': str(obj),
        'fields': model_to_dict_verbose(
            obj,
            exclude=[
                'id',
                f'custom{part_type}_ptr',
                f'stock{part_type}_ptr',
                'quantity',
            ],
        ),
    }
    return render(request, 'partials/detail_modal.html', context)


# GET: modal body
# POST: validate + create, if error, re-render the modal on the first broken step
#       if success, put new row on table and close dialog
@login_required(login_url='/accounts/login')
def add_keyboard(request):
    manager = KeyboardManager(request.user)
    action_url = reverse('keyboard_add')
    if request.method != 'POST':
        kind = request.GET.get('kind')
        if kind not in const.KEYBOARD_KINDS:
            kind = None
        context = manager.keyboard_form_context(action_url, kind=kind)
        return render(request, 'partials/keyboard_modal.html', context)

    context = manager.keyboard_form_context(action_url, request.POST)
    match context['kind']:
        case 'prebuilt':
            kb = manager.add_prebuilt(context, request.POST)
        case 'custom':
            kb = manager.add_custom(context, request.POST)
        case _:
            return HttpResponse(status=400)

    if kb is None:
        return render(request, 'partials/keyboard_modal.html', context)

    row = manager.keyboard_row(kb)
    messages.success(request, f'Added {keyboard_name(row)} to keyboards.')
    response = render(request, 'partials/keyboard_row.html', {'kb': row})
    return htmx_swap(
        response, '#table-keyboards tbody', 'beforeend', const.CLOSE_DIALOG_EVENT
    )


@login_required(login_url='/accounts/login')
def edit_keyboard(request):
    params = keyboard_params(request)
    if params is None:
        return HttpResponse(status=400)

    manager = KeyboardManager(request.user)
    inventory = manager.keyboard_inventory(*params)
    if inventory is None:
        messages.error(request, 'That keyboard no longer exists.')
        raise Http404

    current = inventory.keyboard.obj
    action_url = f'{reverse("keyboard_edit")}?id={params[0]}&stock={int(params[1])}'
    if request.method != 'POST':
        context = manager.keyboard_form_context(action_url, current=current)
        return render(request, 'partials/keyboard_modal.html', context)

    context = manager.keyboard_form_context(action_url, request.POST, current=current)
    kb = manager.edit_keyboard(inventory, context, request.POST)
    if kb is None:
        return render(request, 'partials/keyboard_modal.html', context)

    row = manager.keyboard_row(kb)
    messages.success(request, f'Saved {keyboard_name(row)}.')
    response = render(request, 'partials/keyboard_row.html', {'kb': row})
    return htmx_swap(
        response, f'#{manager.row_id(current)}', 'outerHTML', const.CLOSE_DIALOG_EVENT
    )


# GET: modal body
# POST: delete it, but keep the checked parts in parts inventory
@login_required(login_url='/accounts/login')
def delete_keyboard(request):
    params = keyboard_params(request)
    if params is None:
        return HttpResponse(status=400)

    manager = KeyboardManager(request.user)
    inventory = manager.keyboard_inventory(*params)
    if inventory is None:
        messages.error(request, 'That keyboard no longer exists.')
        raise Http404

    kb = inventory.keyboard.obj
    if request.method != 'POST':
        context = {
            'kb': kb,
            'parts': manager.keyboard_delete_parts(kb),
            'keep_default': manager.profile.keep_parts_on_delete,
            'action_url': f'{reverse("keyboard_delete")}?id={params[0]}&stock={int(params[1])}',
        }
        return render(request, 'partials/delete_keyboard_modal.html', context)

    row_id = manager.row_id(kb)
    name = keyboard_name(manager.keyboard_row(kb))
    keep = request.POST.getlist('keep')
    manager.delete_keyboard(inventory, keep)
    if keep:
        messages.success(
            request, f'Deleted {name}, moved any requested parts to inventory.'
        )
    else:
        messages.success(request, f'Deleted {name}.')
    return htmx_swap(HttpResponse(), f'#{row_id}', 'delete', const.CLOSE_DIALOG_EVENT)


@login_required(login_url='/accounts/login')
def account(request):
    manager = KeyboardManager(request.user)
    form = ProfileForm(request.POST or None, instance=manager.profile)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Saved preferences.')

    context = {'form': form, 'source_options': const.PART_SOURCE_DEFAULTS}
    if 'HX-Request' in request.headers:
        return render(request, 'partials/account_preferences.html', context)

    stats = manager.dashboard()
    context.update(
        page_title='Account',
        keyboard_count=stats['keyboard_count'],
        part_entries=stats['part_entries'],
    )
    return render(request, 'pages/account.html', context)


# add/change individual parts in inventory
# 1 view for each form to handle xhr post request from edit_keyboard
# Kit, Keycaps, Switch, Stabilizer, Plate, Mod


# unified search for stock parts
def search_stock(request):
    pass


# 1 view for each list of stock parts: Keyboard, Kit, Keycaps, Switch, Stabilizer, Plate
def stock_prebuilts(request):
    context = {'page_title': 'Prebuilt Keyboards'}
    return render(request, 'pages/stock_list.html', context)


def stock_kits(request):
    context = {'page_title': 'Kits'}
    return render(request, 'pages/stock_list.html', context)


def stock_keycaps(request):
    context = {'page_title': 'Keycaps'}
    return render(request, 'pages/stock_list.html', context)


def stock_switches(request):
    context = {'page_title': 'Switches'}
    return render(request, 'pages/stock_list.html', context)


def stock_stabilizers(request):
    context = {'page_title': 'Stabilizers'}
    return render(request, 'pages/stock_list.html', context)


def stock_plates(request):
    context = {'page_title': 'Plates'}
    return render(request, 'pages/stock_list.html', context)


# upload canned parts (needs permission)
