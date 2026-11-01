from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import BadRequest
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.urls import Resolver404, resolve, reverse

from . import const
from .forms import ProfileForm
from .handlers import (
    handle_canned_parts_upload,
    stock_csv_columns,
    stock_csv_template,
)
from .managers import (
    PART_MODELS,
    CatalogManager,
    KeyboardManager,
    ModalForms,
    PartManager,
    RowBuilder,
    parse_quantity,
    part_name,
    part_type_of,
)
from .models import Inventory, StockKeyboard
from .utils import (
    bulk_deleted,
    bulk_ids,
    htmx_swap,
    is_id,
    keyboard_params,
    model_to_dict_verbose,
)


def keyboard_name(row):
    return row.get('kit_str', 'keyboard')


def swap_row(request, template, context, target, swap='outerHTML'):
    response = render(request, template, context)
    return htmx_swap(response, target, swap, const.CLOSE_DIALOG_EVENT)


def standalone_part_or_404(request, part_manager):
    part_id = request.GET.get('id', '')
    if not is_id(part_id):
        raise BadRequest
    inv = part_manager.standalone_part(part_id)
    if inv is None:
        messages.error(request, 'That part no longer exists.')
        raise Http404
    return inv


# home/dashboard
def index(request):
    context = {'page_title': 'Home'}
    if request.user.is_authenticated:
        context.update(KeyboardManager(request.user).dashboard())
        context['quick_actions'] = const.QUICK_ACTIONS
    return render(request, 'pages/index.html', context)


@login_required
def inventory_keyboards(request):
    context = {'page_title': 'Keyboard Inventory'}
    context['inventory'] = KeyboardManager(request.user).keyboard_rows()
    context['filters'] = list(const.KEYBOARD_KINDS.items())
    add = request.GET.get('add')
    context['open_add'] = add if add in const.KEYBOARD_KINDS else None
    # cut off text for part names after maybe 50 characters?
    # cut off text for mods + notes after some longer amount of characters
    return render(request, 'pages/inventory_keyboards.html', context)


@login_required
def inventory_parts(request):
    context = {'page_title': 'Parts Inventory'}
    context['inventory'] = PartManager(request.user).part_rows()
    context['part_columns'] = RowBuilder.part_columns()
    context['filters'] = list(const.PART_PLURALS.items())
    add = request.GET.get('add')
    if add is not None:
        context['open_add'] = add if add in PART_MODELS else ''
    return render(request, 'pages/inventory_parts.html', context)


# GET: modal body, pick a part type then stock or custom
# POST: add it to the parts inventory, or bump quantity if exists
@login_required
def add_part(request):
    modal_forms = ModalForms(request.user)
    part_manager = PartManager(request.user)
    if request.method != 'POST':
        part_type = request.GET.get('type')
        if part_type not in PART_MODELS:
            part_type = None
        return render(
            request,
            'partials/modals/part_add_modal.html',
            modal_forms.add_part_context(part_type=part_type),
        )

    context = modal_forms.add_part_context(request.POST)
    if context['part_type'] not in PART_MODELS:
        return HttpResponse(status=400)

    part_type = context['part_type']
    part = next(p for p in context['parts'] if p.type == part_type)
    choice = part.validate(request.POST)
    quantity = parse_quantity(request.POST.get('quantity'))
    if quantity is None:
        context['quantity_error'] = const.QUANTITY_ERROR
    if choice is None or quantity is None:
        context['step'] = part_type
        return render(request, 'partials/modals/part_add_modal.html', context)

    inv, stacked = part_manager.add_part(part_type, choice, quantity)
    row = RowBuilder.part_row(inv)
    if stacked:
        messages.success(
            request, f'Updated quantity of {row["name"]} to {inv.quantity}.'
        )
    else:
        messages.success(request, f'Added {row["name"]} to parts.')
    target, swap = (
        (f'#part-{inv.pk}', 'outerHTML')
        if stacked
        else ('#table-parts tbody', 'beforeend')
    )
    return swap_row(request, 'partials/rows/part_row.html', {'part': row}, target, swap)


@login_required
def edit_part(request):
    part_manager = PartManager(request.user)
    modal_forms = ModalForms(request.user)
    inv = standalone_part_or_404(request, part_manager)

    post = request.POST if request.method == 'POST' else None
    action_url = f'{reverse("part_edit")}?id={inv.pk}'
    context = modal_forms.edit_part_context(inv, action_url, post)
    context['delete_url'] = f'{reverse("part_delete")}?ids={inv.pk}'
    context['promote_url'] = None
    if request.user.has_perm('boards.can_upload_stock_data'):
        context['promote_url'] = f'{reverse("part_promote")}?id={inv.pk}'
    if post is None:
        return render(request, 'partials/modals/part_edit_modal.html', context)

    form = context['form']
    quantity = parse_quantity(post.get('quantity'))
    if quantity is None:
        context['quantity_error'] = const.QUANTITY_ERROR
    form_valid = form is None or form.is_valid()
    if quantity is None or not form_valid:
        return render(request, 'partials/modals/part_edit_modal.html', context)

    inv = part_manager.edit_part(inv, form, quantity)

    row = RowBuilder.part_row(inv)
    messages.success(request, f'Saved {row["name"]}.')
    return swap_row(
        request, 'partials/rows/part_row.html', {'part': row}, f'#part-{inv.pk}'
    )


@permission_required('boards.can_upload_stock_data', raise_exception=True)
def promote_part(request):
    part_manager = PartManager(request.user)
    inv = standalone_part_or_404(request, part_manager)

    part_type = part_type_of(inv)
    wrapper = getattr(inv, part_type)
    if not wrapper.custom_id:
        return HttpResponse(status=400)

    name = part_name(wrapper.obj)
    if request.method != 'POST':
        context = {
            'name': name,
            'type_label': const.PART_SINGULARS[part_type],
            'catalog_url': reverse(f'stock_{const.PART_PLURALS[part_type].lower()}'),
            'action_url': f'{reverse("part_promote")}?id={inv.pk}',
        }
        return render(request, 'partials/modals/part_promote_modal.html', context)

    CatalogManager.promote_part(inv)
    messages.success(request, f'Added {name} to the catalog.')
    row = RowBuilder.part_row(part_manager.standalone_part(inv.pk))
    return swap_row(
        request, 'partials/rows/part_row.html', {'part': row}, f'#{row["row_id"]}'
    )


@login_required
def part_quantity(request):
    if request.method != 'POST':
        return HttpResponse(status=400)

    part_manager = PartManager(request.user)
    inv = standalone_part_or_404(request, part_manager)

    quantity = parse_quantity(request.POST.get('quantity'))
    if quantity is None:
        messages.error(request, const.QUANTITY_ERROR)
    elif quantity != inv.quantity:
        inv.quantity = quantity
        inv.save(update_fields=['quantity'])
        messages.success(
            request,
            f'Updated quantity of {RowBuilder.part_row(inv)["name"]} to {quantity}.',
        )

    return render(
        request, 'partials/rows/part_row.html', {'part': RowBuilder.part_row(inv)}
    )


def delete_modal(request, context):
    return render(request, 'partials/modals/delete_modal.html', context)


def delete_title(names, plural, suffix=''):
    if len(names) == 1:
        return f'Delete {names[0]}{suffix}?'
    return f'Delete {len(names)} {plural}{suffix}?'


def deleted_label(names, plural):
    return names[0] if len(names) == 1 else f'{len(names)} {plural}'


@login_required
def delete_parts(request):
    ids = [value for value in bulk_ids(request) if is_id(value)]
    part_manager = PartManager(request.user)
    invs = list(part_manager.standalone_parts().filter(pk__in=ids).order_by('pk'))
    if not invs:
        return HttpResponse(status=400)

    rows = [RowBuilder.part_row(inv) for inv in invs]
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
        part_manager.delete_part(inv)
    messages.success(request, f'Removed {deleted_label(names, "parts")} from parts.')
    return bulk_deleted([row['row_id'] for row in rows])


@login_required
def delete_keyboards(request):
    kb_manager = KeyboardManager(request.user)
    inventories = []
    for value in bulk_ids(request):
        kind, _, kb_id = value.partition('-')
        if kind in ('stock', 'custom') and is_id(kb_id):
            inventory = kb_manager.keyboard_inventory(kb_id, kind == 'stock')
            if inventory is not None:
                inventories.append((value, inventory))
    if not inventories:
        return HttpResponse(status=400)

    keyboards = [inventory.keyboard.obj for _, inventory in inventories]
    names = [keyboard_name(RowBuilder.keyboard_row(kb)) for kb in keyboards]
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
            context['parts'] = KeyboardManager.keyboard_delete_parts(keyboards[0])
            context['keep_default'] = kb_manager.profile.keep_parts_on_delete
        else:
            context['reminder'] = (
                'Their parts are deleted too. To keep any parts, delete each '
                'keyboard from its edit popup instead.'
            )
        return delete_modal(request, context)

    keep = request.POST.getlist('keep') if single else []
    row_ids = []
    for kb, (_, inventory) in zip(keyboards, inventories, strict=True):
        row_ids.append(RowBuilder.row_id(kb))
        kb_manager.delete_keyboard(inventory, keep)
    label = deleted_label(names, 'keyboards')
    if keep:
        messages.success(
            request, f'Deleted {label}, moved any requested parts to inventory.'
        )
    else:
        messages.success(request, f'Deleted {label}.')
    return bulk_deleted(row_ids)


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

    if part_type not in PART_MODELS or not is_id(part_id) or stock not in ('0', '1'):
        return HttpResponse(status=400)

    # 404 for someone else's custom part too, so ids aren't confirmed
    obj = PartManager(request.user).visible_part(part_type, part_id, stock == '1')
    if obj is None:
        raise Http404

    context = {
        'name': part_name(obj),
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
    return render(request, 'partials/modals/detail_modal.html', context)


# GET: modal body
# POST: validate + create, if error, re-render the modal on the first broken step
#       if success, put new row on table and close dialog
@login_required
def add_keyboard(request):
    modal_forms = ModalForms(request.user)
    kb_manager = KeyboardManager(request.user)
    action_url = reverse('keyboard_add')
    if request.method != 'POST':
        kind = request.GET.get('kind')
        if kind not in const.KEYBOARD_KINDS:
            kind = None
        context = modal_forms.keyboard_form_context(action_url, kind=kind)
        return render(request, 'partials/modals/keyboard_modal.html', context)

    context = modal_forms.keyboard_form_context(action_url, request.POST)
    match context['kind']:
        case 'prebuilt':
            kb, error = modal_forms.validate_prebuilt(request.POST)
            if error is not None:
                context['step'] = 'prebuilt'
                context['prebuilt_error'] = error
                return render(request, 'partials/modals/keyboard_modal.html', context)
            kb_manager.collect_prebuilt(kb)
        case 'custom':
            submission = ModalForms.validate_parts(
                request.POST, context, count_switches=True
            )
            if submission.step is not None:
                context['step'] = submission.step
                return render(request, 'partials/modals/keyboard_modal.html', context)
            kb = kb_manager.add_custom(submission)
        case _:
            return HttpResponse(status=400)

    row = RowBuilder.keyboard_row(kb)
    messages.success(request, f'Added {keyboard_name(row)} to keyboards.')
    return swap_row(
        request,
        'partials/rows/keyboard_row.html',
        {'kb': row},
        '#table-keyboards tbody',
        'beforeend',
    )


@login_required
def edit_keyboard(request):
    params = keyboard_params(request)
    if params is None:
        return HttpResponse(status=400)

    kb_manager = KeyboardManager(request.user)
    modal_forms = ModalForms(request.user)
    inventory = kb_manager.keyboard_inventory(*params)
    if inventory is None:
        messages.error(request, 'That keyboard no longer exists.')
        raise Http404

    current = inventory.keyboard.obj
    action_url = f'{reverse("keyboard_edit")}?id={params[0]}&stock={int(params[1])}'
    delete_url = f'{reverse("keyboard_delete")}?ids={"stock" if params[1] else "custom"}-{params[0]}'
    post = request.POST if request.method == 'POST' else None
    context = modal_forms.keyboard_form_context(action_url, post, current=current)
    context['delete_url'] = delete_url
    if post is None:
        if request.GET.get('step') in PART_MODELS:
            context['step'] = request.GET['step']
        return render(request, 'partials/modals/keyboard_modal.html', context)

    submission = ModalForms.validate_parts(post, context, count_switches=True)
    if submission.step is not None:
        context['step'] = submission.step
        return render(request, 'partials/modals/keyboard_modal.html', context)

    kb = kb_manager.edit_keyboard(inventory, submission)
    row = RowBuilder.keyboard_row(kb)
    messages.success(request, f'Saved {keyboard_name(row)}.')
    return swap_row(
        request,
        'partials/rows/keyboard_row.html',
        {'kb': row},
        f'#{RowBuilder.row_id(current)}',
    )


@login_required
def account(request):
    kb_manager = KeyboardManager(request.user)
    form = ProfileForm(request.POST or None, instance=kb_manager.profile)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Saved preferences.')

    context = {'form': form, 'source_options': const.PART_SOURCE_DEFAULTS}
    if 'HX-Request' in request.headers:
        return render(request, 'partials/sections/account_preferences.html', context)

    context.update(page_title='Account', **kb_manager.inventory_counts())
    return render(request, 'pages/account.html', context)


def stock_prebuilts(request):
    catalog_manager = CatalogManager(request.user)
    rows = catalog_manager.stock_prebuilt_rows()
    context = {
        'page_title': 'Prebuilt Keyboards',
        'prebuilts': rows,
        'facets': RowBuilder.filter_facets(
            rows, request.GET, const.STOCK_PREBUILT_FACETS
        ),
        'query': request.GET.get('q', ''),
    }
    return render(request, 'pages/stock_prebuilts.html', context)


@permission_required('boards.can_upload_stock_data', raise_exception=True)
def add_stock_prebuilt(request):
    modal_forms = ModalForms(request.user)
    action_url = reverse('stock_prebuilt_add')
    if request.method != 'POST':
        return render(
            request,
            'partials/modals/stock_prebuilt_modal.html',
            modal_forms.stock_keyboard_form_context(action_url),
        )

    context = modal_forms.stock_keyboard_form_context(action_url, request.POST)
    submission = ModalForms.validate_parts(request.POST, context)
    if submission.step is not None:
        context['step'] = submission.step
        return render(request, 'partials/modals/stock_prebuilt_modal.html', context)

    stock_kb = CatalogManager.save_stock_keyboard(submission)
    row = RowBuilder.stock_prebuilt_row(stock_kb)
    messages.success(request, f'Added {row["name"]} to the catalog.')
    return swap_row(
        request,
        'partials/rows/stock_prebuilt_row.html',
        {'kb': row},
        '#table-prebuilts tbody',
        'beforeend',
    )


@permission_required('boards.can_edit_stock_data', raise_exception=True)
def edit_stock_prebuilt(request):
    kb_id = request.GET.get('id', '')
    if not is_id(kb_id):
        return HttpResponse(status=400)

    current = StockKeyboard.objects.filter(pk=kb_id).first()
    if current is None:
        messages.error(request, 'That prebuilt is no longer in the catalog.')
        raise Http404

    modal_forms = ModalForms(request.user)
    catalog_manager = CatalogManager(request.user)
    action_url = f'{reverse("stock_prebuilt_edit")}?id={current.pk}'
    delete_url = None
    if request.user.has_perm('boards.can_delete_stock_data'):
        delete_url = f'{reverse("stock_prebuilt_delete")}?ids={current.pk}'
    post = request.POST if request.method == 'POST' else None
    context = modal_forms.stock_keyboard_form_context(action_url, post, current=current)
    context['delete_url'] = delete_url
    if post is None:
        return render(request, 'partials/modals/stock_prebuilt_modal.html', context)

    submission = ModalForms.validate_parts(post, context)
    if submission.step is not None:
        context['step'] = submission.step
        return render(request, 'partials/modals/stock_prebuilt_modal.html', context)

    stock_kb = CatalogManager.save_stock_keyboard(submission)
    row = RowBuilder.stock_prebuilt_row(
        stock_kb, stock_kb.pk in catalog_manager.owned_prebuilt_ids()
    )
    messages.success(request, f'Saved {row["name"]}.')
    return swap_row(
        request,
        'partials/rows/stock_prebuilt_row.html',
        {'kb': row},
        f'#{row["row_id"]}',
    )


@permission_required('boards.can_delete_stock_data', raise_exception=True)
def delete_stock_prebuilts(request):
    ids = [value for value in bulk_ids(request) if is_id(value)]
    stock_kbs = list(
        StockKeyboard.objects.filter(pk__in=ids).select_related('kit').order_by('pk')
    )
    if not stock_kbs:
        return HttpResponse(status=400)

    rows = [RowBuilder.stock_prebuilt_row(kb) for kb in stock_kbs]
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
        CatalogManager.delete_stock_keyboard(stock_kb)
    label = deleted_label([row['name'] for row in rows], 'prebuilts')
    messages.success(request, f'Removed {label} from the catalog.')
    return bulk_deleted([row['row_id'] for row in rows])


@login_required
def collect_stock_prebuilt(request):
    kb_id = request.GET.get('id', '')
    if request.method != 'POST' or not is_id(kb_id):
        return HttpResponse(status=400)

    stock_kb = StockKeyboard.objects.filter(pk=kb_id).select_related('kit').first()
    if stock_kb is None:
        messages.error(request, 'That prebuilt is no longer in the catalog.')
        raise Http404

    catalog_manager = CatalogManager(request.user)
    kb_manager = KeyboardManager(request.user)
    row = RowBuilder.stock_prebuilt_row(stock_kb, owned=True)
    if stock_kb.pk in catalog_manager.owned_prebuilt_ids():
        messages.info(request, f'{row["name"]} is already in your inventory.')
    else:
        kb_manager.collect_prebuilt(stock_kb)
        messages.success(request, f'Added {row["name"]} to keyboards.')
    return render(request, 'partials/rows/stock_prebuilt_row.html', {'kb': row})


def stock_parts(request, part_type):
    catalog_manager = CatalogManager(request.user)
    rows = catalog_manager.stock_part_rows(part_type)
    columns, facet_specs = RowBuilder.stock_part_specs(part_type)
    context = {
        'page_title': const.PART_PLURALS[part_type],
        'part_type': part_type,
        'type_label': const.PART_SINGULARS[part_type],
        'noun': const.PART_PLURALS[part_type].lower(),
        'parts': rows,
        'columns': columns,
        'facets': RowBuilder.filter_facets(rows, request.GET, facet_specs),
        'query': request.GET.get('q', ''),
    }
    return render(request, 'pages/stock_parts.html', context)


def stock_part_from_request(request):
    part_type = request.GET.get('type')
    part_id = request.GET.get('id', '')
    if part_type not in PART_MODELS or not is_id(part_id):
        raise BadRequest
    obj = CatalogManager.stock_part(part_type, part_id)
    if obj is None:
        messages.error(request, 'That part is no longer in the catalog.')
        raise Http404
    return part_type, obj


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
    if part_type not in PART_MODELS:
        return HttpResponse(status=400)

    form_class = PART_MODELS[part_type].stock_form
    form = form_class(request.POST or None, prefix=part_type)
    action_url = f'{reverse("stock_part_add")}?type={part_type}'
    if request.method == 'POST' and form.is_valid():
        row = RowBuilder.stock_part_row(part_type, form.save())
        messages.success(request, f'Added {row["name"]} to the catalog.')
        return swap_row(
            request,
            'partials/rows/stock_part_row.html',
            {'part': row},
            '#table-stock tbody',
            'beforeend',
        )

    return render(
        request,
        'partials/modals/stock_part_modal.html',
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
        return render(request, 'partials/modals/stock_upload_modal.html', context)

    file = request.FILES.get('file')
    if file is None:
        context['errors'] = [(0, 'Choose a CSV file to upload.')]
    elif file.size > const.STOCK_UPLOAD_MAX_BYTES:
        context['errors'] = [(0, 'That file is too big, split it up and try again.')]
    else:
        result = handle_canned_parts_upload(file)
        context['errors'] = result['errors']
    if context['errors']:
        return render(request, 'partials/modals/stock_upload_modal.html', context)

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
    catalog_manager = CatalogManager(request.user)
    part_type, obj = stock_part_from_request(request)

    form = PART_MODELS[part_type].stock_form(
        request.POST or None, prefix=part_type, instance=obj
    )
    action_url = f'{reverse("stock_part_edit")}?type={part_type}&id={obj.pk}'
    delete_url = None
    if request.user.has_perm('boards.can_delete_stock_data'):
        delete_url = f'{reverse("stock_part_delete")}?type={part_type}&ids={obj.pk}'
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        quantity = catalog_manager.stock_part_quantities(part_type).get(obj.pk, 0)
        row = RowBuilder.stock_part_row(part_type, obj, quantity)
        messages.success(request, f'Saved {row["name"]}.')
        return swap_row(
            request,
            'partials/rows/stock_part_row.html',
            {'part': row},
            f'#{row["row_id"]}',
        )

    return render(
        request,
        'partials/modals/stock_part_modal.html',
        stock_part_modal_context(part_type, form, action_url, delete_url),
    )


@permission_required('boards.can_delete_stock_data', raise_exception=True)
def delete_stock_parts(request):
    part_type = request.GET.get('type')
    if part_type not in PART_MODELS:
        return HttpResponse(status=400)

    ids = [value for value in bulk_ids(request) if is_id(value)]
    objs = list(PART_MODELS[part_type].stock.objects.filter(pk__in=ids).order_by('pk'))
    if not objs:
        return HttpResponse(status=400)

    deletable, blocked = [], []
    for obj in objs:
        usage = CatalogManager.stock_part_usage(part_type, obj)
        if usage['prebuilts']:
            blocked.append((part_name(obj), ', '.join(usage['prebuilts'])))
        else:
            deletable.append(obj)
    plural = const.PART_PLURALS[part_type].lower()
    names = [part_name(obj) for obj in deletable]

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
        row_ids.append(RowBuilder.stock_part_row(part_type, obj)['row_id'])
        CatalogManager.delete_stock_part(part_type, obj)
    message = f'Removed {deleted_label(names, plural)} from the catalog.'
    if blocked:
        message += f' Kept {len(blocked)} used by prebuilts.'
    messages.success(request, message)
    return bulk_deleted(row_ids)


@login_required
def collect_stock_part(request):
    part_manager = PartManager(request.user)
    part_type, obj = stock_part_from_request(request)

    name = part_name(obj)
    context = {
        'name': name,
        'part_type': part_type,
        'type_label': const.PART_SINGULARS[part_type],
        'action_url': f'{reverse("stock_part_collect")}?type={part_type}&id={obj.pk}',
        'quantity': request.POST.get('quantity', '1'),
        'quantity_error': None,
    }
    if request.method != 'POST':
        return render(request, 'partials/modals/stock_part_collect_modal.html', context)

    quantity = parse_quantity(request.POST.get('quantity'))
    if quantity is None:
        context['quantity_error'] = const.QUANTITY_ERROR
        return render(request, 'partials/modals/stock_part_collect_modal.html', context)

    inv, stacked = part_manager.collect_stock_part(part_type, obj, quantity)
    if stacked:
        messages.success(request, f'Updated quantity of {name} to {inv.quantity}.')
    else:
        messages.success(request, f'Added {name} to parts.')
    row = RowBuilder.stock_part_row(part_type, obj, inv.quantity)
    return swap_row(
        request,
        'partials/rows/stock_part_row.html',
        {'part': row},
        f'#{row["row_id"]}',
    )
