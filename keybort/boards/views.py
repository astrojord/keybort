from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import BadRequest
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.template.defaultfilters import pluralize
from django.urls import Resolver404, resolve, reverse
from django.views.decorators.http import require_POST

from . import const
from .forms import ProfileForm, TypingResultForm
from .handlers import (
    handle_canned_parts_upload,
    stock_csv_columns,
    stock_csv_template,
)
from .helpers.forms_context import ModalForms, parse_quantity
from .helpers.parts import PART_TYPES, part_type_of
from .helpers.rows import (
    filter_facets,
    keyboard_ref,
    keyboard_row,
    keyboard_row_id,
    model_to_dict_verbose,
    parse_keyboard_ref,
    part_columns,
    part_row,
    part_row_id,
    prebuilt_row_id,
    stock_part_row,
    stock_part_row_id,
    stock_part_specs,
    stock_prebuilt_row,
)
from .htmx import bulk_deleted, htmx_swap
from .models import Inventory, StockKeyboard, part_name
from .request_params import (
    bulk_ids,
    is_id,
    keyboard_params,
    require_id,
    require_stock_flag,
)
from .services.catalog import (
    CatalogService,
    delete_stock_keyboard,
    delete_stock_part,
    promote_to_catalog,
    save_stock_keyboard,
    stock_part_usage,
)
from .services.inventory import KeyboardService, PartService
from .services.races import TypingService


def swap_row(request, template, context, target, swap='outerHTML'):
    response = render(request, template, context)
    return htmx_swap(response, target, swap, const.CLOSE_DIALOG_EVENT)


def require_part_type(request):
    part_type = request.GET.get('type')
    if part_type not in PART_TYPES:
        raise BadRequest
    return part_type


def found_or_404(request, obj, message):
    if obj is None:
        messages.error(request, message)
        raise Http404
    return obj


def standalone_part_or_404(request, part_service):
    inv = part_service.standalone_part(require_id(request))
    return found_or_404(request, inv, 'That part no longer exists.')


def index(request):
    context = {'page_title': 'Home'}
    if request.user.is_authenticated:
        dashboard = KeyboardService(request.user).dashboard()
        context.update(dashboard)
        context.update(
            TypingService(request.user).race_context(dashboard['owned_keyboards'])
        )
        context['quick_actions'] = const.QUICK_ACTIONS
        context['race_words'] = const.TYPING_RACE_WORDS
        context['race_word_choices'] = const.TYPING_RACE_WORD_CHOICES
        context['race_chars_per_word'] = const.TYPING_CHARS_PER_WORD
    return render(request, 'pages/index.html', context)


@login_required
def stats(request):
    context = {'page_title': 'Stats'}
    collection = KeyboardService(request.user).collection_stats()
    context.update(collection)
    context.update(
        TypingService(request.user).race_context(collection['owned_keyboards'])
    )
    return render(request, 'pages/stats.html', context)


@login_required
@require_POST
def save_typing_result(request):
    form = TypingResultForm(request.POST)
    if not form.is_valid():
        raise BadRequest
    data = form.cleaned_data
    typing_service = TypingService(request.user)
    saved = typing_service.record(
        keyboard_id=data['keyboard'],
        word_count=data['word_count'],
        characters=data['characters'],
        mistakes=data['mistakes'],
        duration_ms=data['duration_ms'],
    )
    if not saved:
        raise BadRequest
    return render(
        request,
        'partials/components/typing_history.html',
        typing_service.history_context(),
    )


@login_required
def inventory_keyboards(request):
    context = {'page_title': 'Keyboard Inventory'}
    context['inventory'] = KeyboardService(request.user).keyboard_rows()
    context['filters'] = list(const.KEYBOARD_KINDS.items())
    add = request.GET.get('add')
    context['open_add'] = add if add in const.KEYBOARD_KINDS else None
    return render(request, 'pages/inventory_keyboards.html', context)


@login_required
def inventory_parts(request):
    context = {'page_title': 'Parts Inventory'}
    context['inventory'] = PartService(request.user).part_rows()
    context['part_columns'] = part_columns()
    context['filters'] = [(key, spec.plural) for key, spec in PART_TYPES.items()]
    add = request.GET.get('add')
    if add is not None:
        context['open_add'] = add if add in PART_TYPES else ''
    return render(request, 'pages/inventory_parts.html', context)


@login_required
def add_part(request):
    modal_forms = ModalForms(request.user)
    part_service = PartService(request.user)
    if request.method != 'POST':
        part_type = request.GET.get('type')
        if part_type not in PART_TYPES:
            part_type = None
        return render(
            request,
            'partials/modals/part_add_modal.html',
            modal_forms.add_part_context(part_type=part_type),
        )

    context = modal_forms.add_part_context(request.POST)
    if context['part_type'] not in PART_TYPES:
        raise BadRequest

    part_type = context['part_type']
    part = next(p for p in context['parts'] if p.type == part_type)
    choice = part.validate(request.POST)
    quantity = parse_quantity(request.POST.get('quantity'))
    if quantity is None:
        context['quantity_error'] = const.QUANTITY_ERROR
    if choice is None or quantity is None:
        context['step'] = part_type
        return render(request, 'partials/modals/part_add_modal.html', context)

    inv, stacked = part_service.add_part(part_type, choice, quantity)
    row = part_row(inv)
    if stacked:
        messages.success(
            request, f'Updated quantity of {row["name"]} to {inv.quantity}.'
        )
    else:
        messages.success(request, f'Added {row["name"]} to parts.')
    target, swap = (
        (f'#{part_row_id(inv)}', 'outerHTML')
        if stacked
        else ('#table-parts tbody', 'beforeend')
    )
    return swap_row(request, 'partials/rows/part_row.html', {'part': row}, target, swap)


@login_required
def edit_part(request):
    part_service = PartService(request.user)
    modal_forms = ModalForms(request.user)
    inv = standalone_part_or_404(request, part_service)

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

    inv = part_service.edit_part(inv, form, quantity)

    row = part_row(inv)
    messages.success(request, f'Saved {row["name"]}.')
    return swap_row(
        request, 'partials/rows/part_row.html', {'part': row}, f'#{part_row_id(inv)}'
    )


@permission_required('boards.can_upload_stock_data', raise_exception=True)
def promote_part(request):
    part_service = PartService(request.user)
    inv = standalone_part_or_404(request, part_service)

    part_type = part_type_of(inv)
    wrapper = getattr(inv, part_type)
    if not wrapper.custom_id:
        raise BadRequest

    name = part_name(wrapper.obj)
    if request.method != 'POST':
        context = {
            'name': name,
            'type_label': PART_TYPES[part_type].singular,
            'catalog_url': reverse(PART_TYPES[part_type].catalog_url_name),
            'action_url': f'{reverse("part_promote")}?id={inv.pk}',
        }
        return render(request, 'partials/modals/part_promote_modal.html', context)

    promote_to_catalog(inv)
    messages.success(request, f'Added {name} to the catalog.')
    row = part_row(part_service.standalone_part(inv.pk))
    return swap_row(
        request, 'partials/rows/part_row.html', {'part': row}, f'#{row["row_id"]}'
    )


@login_required
def part_quantity(request):
    if request.method != 'POST':
        raise BadRequest

    part_service = PartService(request.user)
    inv = standalone_part_or_404(request, part_service)

    quantity = parse_quantity(request.POST.get('quantity'))
    if quantity is None:
        messages.error(request, const.QUANTITY_ERROR)
    elif quantity != inv.quantity:
        inv.quantity = quantity
        inv.save(update_fields=['quantity'])
        messages.success(
            request, f'Updated quantity of {part_name(inv.obj)} to {quantity}.'
        )

    return render(request, 'partials/rows/part_row.html', {'part': part_row(inv)})


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
    part_service = PartService(request.user)
    invs = list(part_service.standalone_parts().filter(pk__in=ids).order_by('pk'))
    if not invs:
        raise BadRequest

    names = [part_name(inv.obj) for inv in invs]
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

    row_ids = [part_row_id(inv) for inv in invs]
    for inv in invs:
        part_service.delete_part(inv)
    messages.success(request, f'Removed {deleted_label(names, "parts")} from parts.')
    return bulk_deleted(row_ids)


@login_required
def delete_keyboards(request):
    kb_service = KeyboardService(request.user)
    inventories = []
    for value in bulk_ids(request):
        params = parse_keyboard_ref(value)
        if params is not None:
            inventory = kb_service.keyboard_inventory(*params)
            if inventory is not None:
                inventories.append((value, inventory))
    if not inventories:
        raise BadRequest

    keyboards = [inventory.keyboard.obj for _, inventory in inventories]
    names = [str(kb) for kb in keyboards]
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
            context['parts'] = KeyboardService.keyboard_delete_parts(keyboards[0])
            context['keep_default'] = kb_service.profile.keep_parts_on_delete
        else:
            context['reminder'] = (
                'Their parts are deleted too. To keep any parts, delete each '
                'keyboard from its edit popup instead.'
            )
        return delete_modal(request, context)

    keep = request.POST.getlist('keep') if single else []
    row_ids = []
    for kb, (_, inventory) in zip(keyboards, inventories, strict=True):
        row_ids.append(keyboard_row_id(kb))
        kb_service.delete_keyboard(inventory, keep)
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


def part_detail(request):
    part_type = require_part_type(request)
    part_id = require_id(request)
    stock = require_stock_flag(request)

    # 404 for someone else's custom part too, so ids aren't confirmed
    obj = PartService(request.user).visible_part(part_type, part_id, stock)
    if obj is None:
        raise Http404

    context = {
        'name': part_name(obj),
        'type_label': PART_TYPES[part_type].singular,
        'stock': stock,
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


@login_required
def add_keyboard(request):
    modal_forms = ModalForms(request.user)
    kb_service = KeyboardService(request.user)
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
            kb_service.collect_prebuilt(kb)
        case 'custom':
            submission = ModalForms.validate_parts(
                request.POST, context, count_switches=True
            )
            if submission.step is not None:
                context['step'] = submission.step
                return render(request, 'partials/modals/keyboard_modal.html', context)
            kb = kb_service.add_custom(submission)
        case _:
            raise BadRequest

    row = keyboard_row(kb)
    messages.success(request, f'Added {kb} to keyboards.')
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
    kb_service = KeyboardService(request.user)
    modal_forms = ModalForms(request.user)
    inventory = found_or_404(
        request,
        kb_service.keyboard_inventory(*params),
        'That keyboard no longer exists.',
    )

    current = inventory.keyboard.obj
    action_url = f'{reverse("keyboard_edit")}?id={params[0]}&stock={int(params[1])}'
    delete_url = f'{reverse("keyboard_delete")}?ids={keyboard_ref(current)}'
    post = request.POST if request.method == 'POST' else None
    context = modal_forms.keyboard_form_context(action_url, post, current=current)
    context['delete_url'] = delete_url
    if post is None:
        if request.GET.get('step') in PART_TYPES:
            context['step'] = request.GET['step']
        return render(request, 'partials/modals/keyboard_modal.html', context)

    submission = ModalForms.validate_parts(post, context, count_switches=True)
    if submission.step is not None:
        context['step'] = submission.step
        return render(request, 'partials/modals/keyboard_modal.html', context)

    kb = kb_service.edit_keyboard(inventory, submission)
    row = keyboard_row(kb)
    messages.success(request, f'Saved {kb}.')
    return swap_row(
        request,
        'partials/rows/keyboard_row.html',
        {'kb': row},
        f'#{keyboard_row_id(current)}',
    )


@login_required
def account(request):
    kb_service = KeyboardService(request.user)
    form = ProfileForm(request.POST or None, instance=kb_service.profile)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Saved preferences.')

    context = {'form': form, 'source_options': const.PART_SOURCE_DEFAULTS}
    if 'HX-Request' in request.headers:
        # re-render the page carpet too so toggling it applies without a reload
        context.update(carpet_oob=True, carpet_id='carpet-main')
        return render(request, 'partials/sections/account_preferences.html', context)

    context.update(page_title='Account', **kb_service.inventory_counts())
    return render(request, 'pages/account.html', context)


def stock_prebuilts(request):
    catalog_service = CatalogService(request.user)
    rows = catalog_service.stock_prebuilt_rows()
    context = {
        'page_title': 'Prebuilt Keyboards',
        'prebuilts': rows,
        'facets': filter_facets(rows, request.GET, const.STOCK_PREBUILT_FACETS),
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

    stock_kb = save_stock_keyboard(submission)
    row = stock_prebuilt_row(stock_kb)
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
    current = found_or_404(
        request,
        StockKeyboard.objects.filter(pk=require_id(request)).first(),
        'That prebuilt is no longer in the catalog.',
    )

    modal_forms = ModalForms(request.user)
    catalog_service = CatalogService(request.user)
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

    stock_kb = save_stock_keyboard(submission)
    row = stock_prebuilt_row(
        stock_kb, stock_kb.pk in catalog_service.owned_prebuilt_ids()
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
        raise BadRequest

    names = [str(kb) for kb in stock_kbs]
    if request.method != 'POST':
        owners = (
            Inventory.objects.filter(keyboard__stock__in=stock_kbs)
            .values('user')
            .distinct()
            .count()
        )
        description = "These are removed for everyone and can't be undone."
        if owners:
            description += (
                f' {owners} user{pluralize(owners, " has,s have")}'
                f' {pluralize(len(names), "it,some of them")} in their inventory.'
                ' Their copies will become custom builds with the same parts.'
            )
        return delete_modal(
            request,
            {
                'title': delete_title(names, 'prebuilts', ' from the catalog'),
                'description': description,
                'items': names,
                'ids': [kb.pk for kb in stock_kbs],
                'action_url': reverse('stock_prebuilt_delete'),
            },
        )

    row_ids = [prebuilt_row_id(kb) for kb in stock_kbs]
    for stock_kb in stock_kbs:
        delete_stock_keyboard(stock_kb)
    label = deleted_label(names, 'prebuilts')
    messages.success(request, f'Removed {label} from the catalog.')
    return bulk_deleted(row_ids)


@login_required
def collect_stock_prebuilt(request):
    if request.method != 'POST':
        raise BadRequest
    stock_kb = found_or_404(
        request,
        StockKeyboard.objects.filter(pk=require_id(request))
        .select_related('kit')
        .first(),
        'That prebuilt is no longer in the catalog.',
    )

    catalog_service = CatalogService(request.user)
    kb_service = KeyboardService(request.user)
    row = stock_prebuilt_row(stock_kb, owned=True)
    if stock_kb.pk in catalog_service.owned_prebuilt_ids():
        messages.info(request, f'{row["name"]} is already in your inventory.')
    else:
        kb_service.collect_prebuilt(stock_kb)
        messages.success(request, f'Added {row["name"]} to keyboards.')
    return render(request, 'partials/rows/stock_prebuilt_row.html', {'kb': row})


def stock_parts(request, part_type):
    catalog_service = CatalogService(request.user)
    rows = catalog_service.stock_part_rows(part_type)
    columns, facet_specs = stock_part_specs(part_type)
    context = {
        'page_title': PART_TYPES[part_type].plural,
        'part_type': part_type,
        'type_label': PART_TYPES[part_type].singular,
        'noun': PART_TYPES[part_type].plural.lower(),
        'parts': rows,
        'columns': columns,
        'facets': filter_facets(rows, request.GET, facet_specs),
        'query': request.GET.get('q', ''),
    }
    return render(request, 'pages/stock_parts.html', context)


def stock_part_from_request(request):
    part_type = require_part_type(request)
    stock_model = PART_TYPES[part_type].stock
    obj = stock_model.objects.filter(pk=require_id(request)).first()
    return part_type, found_or_404(
        request, obj, 'That part is no longer in the catalog.'
    )


def stock_part_modal_context(part_type, form, action_url, delete_url=None):
    return {
        'form': form,
        'type_label': PART_TYPES[part_type].singular,
        'action_url': action_url,
        'editing': form.instance.pk is not None,
        'delete_url': delete_url,
    }


@permission_required('boards.can_upload_stock_data', raise_exception=True)
def add_stock_part(request):
    part_type = require_part_type(request)

    form_class = PART_TYPES[part_type].stock_form
    form = form_class(request.POST or None, prefix=part_type)
    action_url = f'{reverse("stock_part_add")}?type={part_type}'
    if request.method == 'POST' and form.is_valid():
        row = stock_part_row(part_type, form.save())
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
    added = []
    for part_type, count in result.created.items():
        if count:
            spec = PART_TYPES[part_type]
            nouns = f'{spec.singular},{spec.plural}'
            added.append(f'{count} {pluralize(count, nouns).lower()}')
    skipped = result.skipped
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
        context['errors'] = result.errors
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
    catalog_service = CatalogService(request.user)
    part_type, obj = stock_part_from_request(request)

    form = PART_TYPES[part_type].stock_form(
        request.POST or None, prefix=part_type, instance=obj
    )
    action_url = f'{reverse("stock_part_edit")}?type={part_type}&id={obj.pk}'
    delete_url = None
    if request.user.has_perm('boards.can_delete_stock_data'):
        delete_url = f'{reverse("stock_part_delete")}?type={part_type}&ids={obj.pk}'
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        quantity = catalog_service.stock_part_quantities(part_type).get(obj.pk, 0)
        row = stock_part_row(part_type, obj, quantity)
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
    part_type = require_part_type(request)

    ids = [value for value in bulk_ids(request) if is_id(value)]
    objs = list(PART_TYPES[part_type].stock.objects.filter(pk__in=ids).order_by('pk'))
    if not objs:
        raise BadRequest

    deletable, blocked = [], []
    for obj in objs:
        usage = stock_part_usage(part_type, obj)
        if usage['prebuilts']:
            blocked.append((part_name(obj), ', '.join(usage['prebuilts'])))
        else:
            deletable.append(obj)
    plural = PART_TYPES[part_type].plural.lower()
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
        raise BadRequest

    row_ids = [stock_part_row_id(part_type, obj) for obj in deletable]
    for obj in deletable:
        delete_stock_part(part_type, obj)
    message = f'Removed {deleted_label(names, plural)} from the catalog.'
    if blocked:
        message += f' Kept {len(blocked)} used by prebuilts.'
    messages.success(request, message)
    return bulk_deleted(row_ids)


@login_required
def collect_stock_part(request):
    part_service = PartService(request.user)
    part_type, obj = stock_part_from_request(request)

    name = part_name(obj)
    context = {
        'name': name,
        'part_type': part_type,
        'type_label': PART_TYPES[part_type].singular,
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

    inv, stacked = part_service.collect_stock_part(part_type, obj, quantity)
    if stacked:
        messages.success(request, f'Updated quantity of {name} to {inv.quantity}.')
    else:
        messages.success(request, f'Added {name} to parts.')
    row = stock_part_row(part_type, obj, inv.quantity)
    return swap_row(
        request,
        'partials/rows/stock_part_row.html',
        {'part': row},
        f'#{row["row_id"]}',
    )
