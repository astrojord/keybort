# Django structure
`boards` is the only Django app with full "typical" content. `config` just has Django's settings and the root URLs, which send `admin/` to Django admin, `accounts/` to allauth, and everything else to `boards.urls`. See [data-model](data-model.md) for model class setup.

#### Request flow
```
urls.py -> views.py -> services/ -> models.py
                   \-> helpers/
                   \-> forms.py
                   \-> handlers.py (CSV upload only)
```

Views are deliberately small and hand off anything that requires more than one model to the appropriate class in `services`.

#### Non-standard modules
| File | Contents |
| --- | --- |
| `services/` | Per-user classes that wrap ORM queries and writes, plus the stock catalog write functions |
| `helpers/` | Part registry, row/stats builders, and modal form context |
| `handlers.py` | Parses + validates stock part CSVs, likely to be expanded later for other upload handlers |
| `middleware.py` | `HtmxMessagesMiddleware`, see [frontend](frontend.md) |
| `request_params.py` | Request parsing (`is_id`, `require_id`, `keyboard_params`, `bulk_ids`) |
| `htmx.py` | HTMX response helpers (`htmx_swap`, `bulk_deleted`) |
| `const.py` | Choices, labels, table columns, limits |

#### services/
Classes here are supposed to be instantiated once per request, ie `SomeService(request.user)`.

- `inventory.py`
  - `PartService` - standalone parts in a given user's inventory
  - `KeyboardService` - a given user's keyboards, dashboard numbers, and collection stats
- `races.py` - `TypingService`, saves typing race results + builds the history/sparklines
- `catalog.py` - `CatalogService` for a user's view of the stock catalog, plus functions for stock part/prebuilt writes (promote, delete, save)
- `base.py` - `UserScoped`, the shared `user`/`profile` base

#### helpers/
- `parts.py` - dataclasses for each part type with relevant info/strings/classes, + contains small part helpers (`part_obj`, `part_in_use`, ...)
- `rows.py` - turns models into the dicts the table row templates expect, plus row ids and keyboard refs
- `forms_context.py` - `ModalForms` builds context dicts for the add/edit modals, `PartChoice` / `KeyboardSubmission` are dataclasses for user responses in them
- `stats.py` - stats page breakdowns and the typing sparkline

#### Access
- Public: home, the stock catalog pages, and `get_part_detail` (404s on custom parts you don't own)
- Login required: anything under `inventory/`, `account`, `stats`, typing results, and adding stock items to your inventory
- Stock data permissions, defined on the empty `BoardsPermissions` model:
    - `can_upload_stock_data` - add stock items, CSV upload, promote a custom part to stock
    - `can_edit_stock_data`
    - `can_delete_stock_data`

#### Auth
Handed off to django-allauth. Social account integration will be added in the future.

#### Tests
Tests are unified in `keybort/tests/` rather than in the usual Django `tests.py` file per app. Shared factories like `make_user` and `stock_kit` are in `tests/base.py`. Test run info is in the main README.
