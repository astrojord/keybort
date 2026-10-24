from django.contrib import messages
from django.contrib.auth.decorators import (
    login_required,
    permission_required,
    user_passes_test,
)
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.urls import Resolver404, resolve, reverse

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
from .handlers import (
    handle_canned_parts_upload,
    stock_csv_columns,
    stock_csv_template,
)
from .managers import KeyboardManager
from .models import Inventory, StockKeyboard
from .utils import (
    bulk_deleted,
    bulk_ids,
    htmx_swap,
    keyboard_params,
    model_to_dict_verbose,
)


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
    urls = {'delete_url': f'{reverse("part_delete")}?ids={inv.pk}', 'promote_url': None}
    if request.user.has_perm('boards.can_upload_stock_data'):
        urls['promote_url'] = f'{reverse("part_promote")}?id={inv.pk}'
    if request.method != 'POST':
        context = manager.edit_part_context(inv, action_url)
        context.update(urls)
        return render(request, 'partials/part_edit_modal.html', context)

    context = manager.edit_part_context(inv, action_url, request.POST)
    context.update(urls)
    inv = manager.edit_part(context, request.POST)
    if inv is None:
        return render(request, 'partials/part_edit_modal.html', context)

    row = manager.part_row(inv)
    messages.success(request, f'Saved {row["name"]}.')
    response = render(request, 'partials/part_row.html', {'part': row})
    return htmx_swap(response, f'#part-{inv.pk}', 'outerHTML', const.CLOSE_DIALOG_EVENT)


@permission_required('boards.can_upload_stock_data', raise_exception=True)
def promote_part(request):
    part_id = request.GET.get('id', '')
    if not part_id.isdigit():
        return HttpResponse(status=400)

    manager = KeyboardManager(request.user)
    inv = manager.standalone_part(part_id)
    if inv is None:
        messages.error(request, 'That part no longer exists.')
        raise Http404

    part_type = manager.part_type_of(inv)
    wrapper = getattr(inv, part_type)
    if not wrapper.custom_id:
        return HttpResponse(status=400)

    name = manager.part_name(wrapper.obj)
    if request.method != 'POST':
        context = {
            'name': name,
            'type_label': const.PART_SINGULARS[part_type],
            'catalog_url': reverse(f'stock_{const.PART_PLURALS[part_type].lower()}'),
            'action_url': f'{reverse("part_promote")}?id={inv.pk}',
        }
        return render(request, 'partials/part_promote_modal.html', context)

    manager.promote_part(inv)
    messages.success(request, f'Added {name} to the catalog.')
    row = manager.part_row(manager.standalone_part(inv.pk))
    response = render(request, 'partials/part_row.html', {'part': row})
    return htmx_swap(
        response, f'#{row["row_id"]}', 'outerHTML', const.CLOSE_DIALOG_EVENT
    )


@login_required(login_url='/accounts/login')
def part_quantity(request):
    part_id = request.GET.get('id', '')
    if request.method != 'POST' or not part_id.isdigit():
        return HttpResponse(status=400)

    manager = KeyboardManager(request.user)
    inv = manager.standalone_part(part_id)
    if inv is None:
        messages.error(request, 'That part no longer exists.')
        raise Http404

    quantity = manager.parse_quantity(request.POST.get('quantity'))
    if quantity is None:
        messages.error(request, const.QUANTITY_ERROR)
    elif quantity != inv.quantity:
        inv.quantity = quantity
        inv.save(update_fields=['quantity'])
        messages.success(
            request,
            f'Updated quantity of {manager.part_row(inv)["name"]} to {quantity}.',
        )

    return render(request, 'partials/part_row.html', {'part': manager.part_row(inv)})


def delete_modal(request, context):
    return render(request, 'partials/delete_modal.html', context)


def delete_title(names, plural, suffix=''):
    if len(names) == 1:
        return f'Delete {names[0]}{suffix}?'
    return f'Delete {len(names)} {plural}{suffix}?'


def deleted_label(names, plural):
    return names[0] if len(names) == 1 else f'{len(names)} {plural}'


@login_required(login_url='/accounts/login')
def delete_parts(request):
    ids = [value for value in bulk_ids(request) if value.isdigit()]
    manager = KeyboardManager(request.user)
    invs = list(manager.standalone_parts().filter(pk__in=ids).order_by('pk'))
    if not invs:
        return HttpResponse(status=400)

    rows = [manager.part_row(inv) for inv in invs]
    names = [row['name'] for row in rows]
    if request.method != 'POST':
        return delete_modal(
            request,
            {
                'title': delete_title(names, 'parts'),
                'description': 'Custom parts are deleted for good. Stock parts stay in the catalog.',
                'items': names,
                'ids': [inv.pk for inv in invs],
                'action_url': reverse('part_delete'),
            },
        )

    for inv in invs:
        manager.delete_part(inv)
    messages.success(request, f'Removed {deleted_label(names, "parts")} from parts.')
    return bulk_deleted([row['row_id'] for row in rows], const.CLOSE_DIALOG_EVENT)


@login_required(login_url='/accounts/login')
def delete_keyboards(request):
    manager = KeyboardManager(request.user)
    inventories = []
    for value in bulk_ids(request):
        kind, _, kb_id = value.partition('-')
        if kind in ('stock', 'custom') and kb_id.isdigit():
            inventory = manager.keyboard_inventory(kb_id, kind == 'stock')
            if inventory is not None:
                inventories.append((value, inventory))
    if not inventories:
        return HttpResponse(status=400)

    keyboards = [inventory.keyboard.obj for _, inventory in inventories]
    names = [keyboard_name(manager.keyboard_row(kb)) for kb in keyboards]
    single = len(keyboards) == 1
    if request.method != 'POST':
        context = {
            'title': delete_title(names, 'keyboards'),
            'description': 'Custom builds are deleted for good. Prebuilts stay in the catalog.',
            'items': names,
            'ids': [value for value, _ in inventories],
            'action_url': reverse('keyboard_delete'),
        }
        if single:
            context['parts'] = manager.keyboard_delete_parts(keyboards[0])
            context['keep_default'] = manager.profile.keep_parts_on_delete
        else:
            context['reminder'] = (
                'Their parts are deleted too. To keep any parts, delete each '
                'keyboard from its edit popup instead.'
            )
        return delete_modal(request, context)

    keep = request.POST.getlist('keep') if single else []
    row_ids = []
    for kb, (_, inventory) in zip(keyboards, inventories, strict=True):
        row_ids.append(manager.row_id(kb))
        manager.delete_keyboard(inventory, keep)
    label = deleted_label(names, 'keyboards')
    if keep:
        messages.success(
            request, f'Deleted {label}, moved any requested parts to inventory.'
        )
    else:
        messages.success(request, f'Deleted {label}.')
    return bulk_deleted(row_ids, const.CLOSE_DIALOG_EVENT)


def edit_url(url):
    if not url.startswith('/') or url.startswith('//'):
        return None
    try:
        match = resolve(url.split('?')[0])
    except Resolver404:
        return None
    return url if match.url_name in ('part_edit', 'keyboard_edit') else None


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
        'name': KeyboardManager.part_name(obj),
        'type_label': const.PART_SINGULARS[part_type],
        'stock': stock == '1',
        'edit_url': edit_url(request.GET.get('edit', '')),
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
    delete_url = f'{reverse("keyboard_delete")}?ids={"stock" if params[1] else "custom"}-{params[0]}'
    if request.method != 'POST':
        context = manager.keyboard_form_context(action_url, current=current)
        context['delete_url'] = delete_url
        if request.GET.get('step') in manager.PART_MODELS:
            context['step'] = request.GET['step']
        return render(request, 'partials/keyboard_modal.html', context)

    context = manager.keyboard_form_context(action_url, request.POST, current=current)
    context['delete_url'] = delete_url
    kb = manager.edit_keyboard(inventory, context, request.POST)
    if kb is None:
        return render(request, 'partials/keyboard_modal.html', context)

    row = manager.keyboard_row(kb)
    messages.success(request, f'Saved {keyboard_name(row)}.')
    response = render(request, 'partials/keyboard_row.html', {'kb': row})
    return htmx_swap(
        response, f'#{manager.row_id(current)}', 'outerHTML', const.CLOSE_DIALOG_EVENT
    )


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
    manager = KeyboardManager(request.user)
    rows = manager.stock_prebuilt_rows()
    context = {
        'page_title': 'Prebuilt Keyboards',
        'prebuilts': rows,
        'facets': manager.filter_facets(rows, request.GET, const.STOCK_PREBUILT_FACETS),
        'query': request.GET.get('q', ''),
    }
    return render(request, 'pages/stock_prebuilts.html', context)


@permission_required('boards.can_upload_stock_data', raise_exception=True)
def add_stock_prebuilt(request):
    manager = KeyboardManager(request.user)
    action_url = reverse('stock_prebuilt_add')
    if request.method != 'POST':
        return render(
            request,
            'partials/stock_prebuilt_modal.html',
            manager.stock_keyboard_form_context(action_url),
        )

    context = manager.stock_keyboard_form_context(action_url, request.POST)
    stock_kb = manager.save_stock_keyboard(context, request.POST)
    if stock_kb is None:
        return render(request, 'partials/stock_prebuilt_modal.html', context)

    row = manager.stock_prebuilt_row(stock_kb)
    messages.success(request, f'Added {row["name"]} to the catalog.')
    response = render(request, 'partials/stock_prebuilt_row.html', {'kb': row})
    return htmx_swap(
        response, '#table-prebuilts tbody', 'beforeend', const.CLOSE_DIALOG_EVENT
    )


@permission_required('boards.can_edit_stock_data', raise_exception=True)
def edit_stock_prebuilt(request):
    kb_id = request.GET.get('id', '')
    if not kb_id.isdigit():
        return HttpResponse(status=400)

    current = StockKeyboard.objects.filter(pk=kb_id).first()
    if current is None:
        messages.error(request, 'That prebuilt is no longer in the catalog.')
        raise Http404

    manager = KeyboardManager(request.user)
    action_url = f'{reverse("stock_prebuilt_edit")}?id={current.pk}'
    delete_url = None
    if request.user.has_perm('boards.can_delete_stock_data'):
        delete_url = f'{reverse("stock_prebuilt_delete")}?ids={current.pk}'
    if request.method != 'POST':
        context = manager.stock_keyboard_form_context(action_url, current=current)
        context['delete_url'] = delete_url
        return render(request, 'partials/stock_prebuilt_modal.html', context)

    context = manager.stock_keyboard_form_context(
        action_url, request.POST, current=current
    )
    context['delete_url'] = delete_url
    stock_kb = manager.save_stock_keyboard(context, request.POST)
    if stock_kb is None:
        return render(request, 'partials/stock_prebuilt_modal.html', context)

    row = manager.stock_prebuilt_row(
        stock_kb, stock_kb.pk in manager.owned_prebuilt_ids()
    )
    messages.success(request, f'Saved {row["name"]}.')
    response = render(request, 'partials/stock_prebuilt_row.html', {'kb': row})
    return htmx_swap(
        response, f'#{row["row_id"]}', 'outerHTML', const.CLOSE_DIALOG_EVENT
    )


@permission_required('boards.can_delete_stock_data', raise_exception=True)
def delete_stock_prebuilts(request):
    ids = [value for value in bulk_ids(request) if value.isdigit()]
    stock_kbs = list(
        StockKeyboard.objects.filter(pk__in=ids).select_related('kit').order_by('pk')
    )
    if not stock_kbs:
        return HttpResponse(status=400)

    manager = KeyboardManager(request.user)
    rows = [manager.stock_prebuilt_row(kb) for kb in stock_kbs]
    if request.method != 'POST':
        owners = (
            Inventory.objects.filter(keyboard__stock__in=stock_kbs)
            .values('user')
            .distinct()
            .count()
        )
        description = "These are removed for everyone and can't be undone."
        if owners:
            description += f' {owners} user{" has" if owners == 1 else "s have"} {"it" if len(rows) == 1 else "some of them"} in their inventory. Their copies will become custom builds with the same parts.'
        return delete_modal(
            request,
            {
                'title': delete_title(
                    [row['name'] for row in rows], 'prebuilts', ' from the catalog'
                ),
                'description': description,
                'items': [row['name'] for row in rows],
                'ids': [kb.pk for kb in stock_kbs],
                'action_url': reverse('stock_prebuilt_delete'),
            },
        )

    for stock_kb in stock_kbs:
        manager.delete_stock_keyboard(stock_kb)
    label = deleted_label([row['name'] for row in rows], 'prebuilts')
    messages.success(request, f'Removed {label} from the catalog.')
    return bulk_deleted([row['row_id'] for row in rows], const.CLOSE_DIALOG_EVENT)


@login_required(login_url='/accounts/login')
def collect_stock_prebuilt(request):
    kb_id = request.GET.get('id', '')
    if request.method != 'POST' or not kb_id.isdigit():
        return HttpResponse(status=400)

    stock_kb = StockKeyboard.objects.filter(pk=kb_id).select_related('kit').first()
    if stock_kb is None:
        messages.error(request, 'That prebuilt is no longer in the catalog.')
        raise Http404

    manager = KeyboardManager(request.user)
    row = manager.stock_prebuilt_row(stock_kb, owned=True)
    if stock_kb.pk in manager.owned_prebuilt_ids():
        messages.info(request, f'{row["name"]} is already in your inventory.')
    else:
        manager.collect_prebuilt(stock_kb)
        messages.success(request, f'Added {row["name"]} to keyboards.')
    return render(request, 'partials/stock_prebuilt_row.html', {'kb': row})


def stock_parts(request, part_type):
    manager = KeyboardManager(request.user)
    rows = manager.stock_part_rows(part_type)
    columns, facet_specs = manager.stock_part_specs(part_type)
    context = {
        'page_title': const.PART_PLURALS[part_type],
        'part_type': part_type,
        'type_label': const.PART_SINGULARS[part_type],
        'noun': const.PART_PLURALS[part_type].lower(),
        'parts': rows,
        'columns': columns,
        'facets': manager.filter_facets(rows, request.GET, facet_specs),
        'query': request.GET.get('q', ''),
    }
    return render(request, 'pages/stock_parts.html', context)


def stock_kits(request):
    return stock_parts(request, 'kit')


def stock_keycaps(request):
    return stock_parts(request, 'keycaps')


def stock_switches(request):
    return stock_parts(request, 'switch')


def stock_stabilizers(request):
    return stock_parts(request, 'stabilizer')


def stock_plates(request):
    return stock_parts(request, 'plate')


def stock_part_from_request(request, manager):
    part_type = request.GET.get('type')
    part_id = request.GET.get('id', '')
    if part_type not in manager.PART_MODELS or not part_id.isdigit():
        return part_type, None, HttpResponse(status=400)
    obj = manager.stock_part(part_type, part_id)
    if obj is None:
        messages.error(request, 'That part is no longer in the catalog.')
        raise Http404
    return part_type, obj, None


def stock_part_modal_context(part_type, form, action_url, delete_url=None):
    return {
        'form': form,
        'type_label': const.PART_SINGULARS[part_type],
        'action_url': action_url,
        'editing': form.instance.pk is not None,
        'delete_url': delete_url,
    }


@permission_required('boards.can_upload_stock_data', raise_exception=True)
def add_stock_part(request):
    part_type = request.GET.get('type')
    if part_type not in KeyboardManager.PART_MODELS:
        return HttpResponse(status=400)

    form_class = KeyboardManager.STOCK_FORMS[part_type]
    form = form_class(request.POST or None, prefix=part_type)
    action_url = f'{reverse("stock_part_add")}?type={part_type}'
    if request.method == 'POST' and form.is_valid():
        row = KeyboardManager.stock_part_row(part_type, form.save())
        messages.success(request, f'Added {row["name"]} to the catalog.')
        response = render(request, 'partials/stock_part_row.html', {'part': row})
        return htmx_swap(
            response, '#table-stock tbody', 'beforeend', const.CLOSE_DIALOG_EVENT
        )

    return render(
        request,
        'partials/stock_part_modal.html',
        stock_part_modal_context(part_type, form, action_url),
    )


def upload_summary(result):
    added = [
        f'{count} {(const.PART_SINGULARS if count == 1 else const.PART_PLURALS)[part_type].lower()}'
        for part_type, count in result['created'].items()
        if count
    ]
    skipped = result['skipped']
    skipped_note = f'{skipped} already in the catalog' if skipped else ''
    if not added:
        return (
            messages.INFO,
            f'Nothing new to add, {skipped_note or "the file was empty"}.',
        )
    summary = f'Added {", ".join(added)} to the catalog.'
    if skipped_note:
        summary += f' Skipped {skipped_note}.'
    return messages.SUCCESS, summary


@permission_required('boards.can_upload_stock_data', raise_exception=True)
def upload_stock_parts(request):
    context = {
        'action_url': reverse('stock_part_upload'),
        'columns': stock_csv_columns(),
    }
    if request.method != 'POST':
        return render(request, 'partials/stock_upload_modal.html', context)

    file = request.FILES.get('file')
    if file is None:
        context['errors'] = [(0, 'Choose a CSV file to upload.')]
    elif file.size > const.STOCK_UPLOAD_MAX_BYTES:
        context['errors'] = [(0, 'That file is too big, split it up and try again.')]
    else:
        result = handle_canned_parts_upload(file)
        context['errors'] = result['errors']
    if context['errors']:
        return render(request, 'partials/stock_upload_modal.html', context)

    messages.add_message(request, *upload_summary(result))
    response = HttpResponse()
    response['HX-Refresh'] = 'true'
    return response


@permission_required('boards.can_upload_stock_data', raise_exception=True)
def stock_upload_template(request):
    response = HttpResponse(stock_csv_template(), content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="stock-parts.csv"'
    return response


@permission_required('boards.can_edit_stock_data', raise_exception=True)
def edit_stock_part(request):
    manager = KeyboardManager(request.user)
    part_type, obj, error = stock_part_from_request(request, manager)
    if error:
        return error

    form = manager.STOCK_FORMS[part_type](
        request.POST or None, prefix=part_type, instance=obj
    )
    action_url = f'{reverse("stock_part_edit")}?type={part_type}&id={obj.pk}'
    delete_url = None
    if request.user.has_perm('boards.can_delete_stock_data'):
        delete_url = f'{reverse("stock_part_delete")}?type={part_type}&ids={obj.pk}'
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        quantity = manager.stock_part_quantities(part_type).get(obj.pk, 0)
        row = manager.stock_part_row(part_type, obj, quantity)
        messages.success(request, f'Saved {row["name"]}.')
        response = render(request, 'partials/stock_part_row.html', {'part': row})
        return htmx_swap(
            response, f'#{row["row_id"]}', 'outerHTML', const.CLOSE_DIALOG_EVENT
        )

    return render(
        request,
        'partials/stock_part_modal.html',
        stock_part_modal_context(part_type, form, action_url, delete_url),
    )


@permission_required('boards.can_delete_stock_data', raise_exception=True)
def delete_stock_parts(request):
    part_type = request.GET.get('type')
    if part_type not in KeyboardManager.PART_MODELS:
        return HttpResponse(status=400)

    manager = KeyboardManager(request.user)
    ids = [value for value in bulk_ids(request) if value.isdigit()]
    objs = list(
        manager.PART_MODELS[part_type][2].objects.filter(pk__in=ids).order_by('pk')
    )
    if not objs:
        return HttpResponse(status=400)

    deletable, blocked = [], []
    for obj in objs:
        usage = manager.stock_part_usage(part_type, obj)
        if usage['prebuilts']:
            blocked.append((manager.part_name(obj), ', '.join(usage['prebuilts'])))
        else:
            deletable.append(obj)
    plural = const.PART_PLURALS[part_type].lower()
    names = [manager.part_name(obj) for obj in deletable]

    if request.method != 'POST':
        return delete_modal(
            request,
            {
                'title': delete_title(names, plural, ' from the catalog'),
                'description': "This removes them for everyone and can't be undone. Anyone who has one keeps a custom copy with the same details.",
                'items': names,
                'blocked': blocked,
                'ids': [obj.pk for obj in deletable],
                'action_url': f'{reverse("stock_part_delete")}?type={part_type}',
            },
        )

    if not deletable:
        messages.error(
            request, 'Those are all used by catalog prebuilts, so they stay.'
        )
        return HttpResponse(status=400)

    row_ids = []
    for obj in deletable:
        row_ids.append(manager.stock_part_row(part_type, obj)['row_id'])
        manager.delete_stock_part(part_type, obj)
    message = f'Removed {deleted_label(names, plural)} from the catalog.'
    if blocked:
        message += f' Kept {len(blocked)} used by prebuilts.'
    messages.success(request, message)
    return bulk_deleted(row_ids, const.CLOSE_DIALOG_EVENT)


@login_required(login_url='/accounts/login')
def collect_stock_part(request):
    manager = KeyboardManager(request.user)
    part_type, obj, error = stock_part_from_request(request, manager)
    if error:
        return error

    name = manager.part_name(obj)
    context = {
        'name': name,
        'part_type': part_type,
        'type_label': const.PART_SINGULARS[part_type],
        'action_url': f'{reverse("stock_part_collect")}?type={part_type}&id={obj.pk}',
        'quantity': request.POST.get('quantity', '1'),
        'quantity_error': None,
    }
    if request.method != 'POST':
        return render(request, 'partials/stock_part_collect_modal.html', context)

    quantity = manager.parse_quantity(request.POST.get('quantity'))
    if quantity is None:
        context['quantity_error'] = const.QUANTITY_ERROR
        return render(request, 'partials/stock_part_collect_modal.html', context)

    inv, stacked = manager.collect_stock_part(part_type, obj, quantity)
    if stacked:
        messages.success(request, f'Updated quantity of {name} to {inv.quantity}.')
    else:
        messages.success(request, f'Added {name} to parts.')
    row = manager.stock_part_row(part_type, obj, inv.quantity)
    response = render(request, 'partials/stock_part_row.html', {'part': row})
    return htmx_swap(
        response, f'#{row["row_id"]}', 'outerHTML', const.CLOSE_DIALOG_EVENT
    )


# upload canned parts (needs permission)
