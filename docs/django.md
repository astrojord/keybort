# Django structure
`boards` is the only Django app with full "typical" content. `config` just has Django's settings and the root URLs, which send `admin/` to Django admin, `accounts/` to allauth, and everything else to `boards.urls`. See [data-model](data-model.md) for model class setup.

#### Request flow
```
urls.py -> views.py -> managers.py -> models.py
                   \-> forms.py
                   \-> handlers.py (CSV upload only)
```

Views are deliberately small and hand off anything that requires more than one model to the appropriate class in `managers`.

#### Non-standard modules
| File | Contents |
| --- | --- |
| `managers.py` | Helper classes to abstract dict construction and ORM queries away from view functions |
| `handlers.py` | Parses + validates stock part CSVs, likely to be expanded later for other upload handlers |
| `middleware.py` | `HtmxMessagesMiddleware`, see [frontend](frontend.md) |
| `utils.py` | Request parsing (`is_id`, `keyboard_params`, `bulk_ids`) and HTMX response helpers (`htmx_swap`, `bulk_deleted`) |
| `const.py` | Choices, labels, table columns, limits |

#### managers.py
Most helper classes here are supposed to be instantiated once per request, ie `SomeManager(request.user)`.

- `PART_MODELS` - maps each part type (`kit`, `switch`, `keycaps`, `plate`, `stabilizer`) to its wrapper model, custom model, stock model, and forms
- `RowBuilder` - turns models into the dicts the table row templates expect
- `ModalForms` - builds context dicts for the add/edit modals
- `PartChoice` / `KeyboardSubmission` - dataclasses for user responses in add/edit modals
- `PartManager` - standalone parts in a given user's inventory
- `KeyboardManager` - a given user's keyboards and dashboard numbers
- `TypingManager` - saves typing race results + builds the history/sparklines
- `CatalogManager` - CRUD operations on stock part data

#### Access
- Public: home, the stock catalog pages, and `get_part_detail` (404s on custom parts you don't own)
- Login required: anything under `inventory/`, `account`, typing results, and adding stock items to your inventory
- Stock data permissions, defined on the empty `BoardsPermissions` model:
    - `can_upload_stock_data` - add stock items, CSV upload, promote a custom part to stock
    - `can_edit_stock_data`
    - `can_delete_stock_data`

#### Auth
Handed off to django-allauth. Social account integration will be added in the future.

#### Tests
Tests are unified in `keybort/tests/` rather than in the usual Django `tests.py` file per app. Shared factories like `make_user` and `stock_kit` are in `tests/base.py`. Test run info is in the main README.
