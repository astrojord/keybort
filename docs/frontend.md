# Frontend
Fully served by Django's template engine, with HTMX for anything that shouldn't reload the page. Styling is [Basecoat UI](https://basecoatui.com) + Tailwind. No JS framework included or expected at any point in the future.

#### Templates
| Directory | Contents |
| --- | --- |
| `base/` | Page shell: `base.html`, head, header, sidebar, toaster |
| `pages/` | One per full page, all extend `base/base.html` |
| `partials/rows/` | Single table rows for various tables across the app |
| `partials/modals/` | Modal bodies to be loaded by HTMX |
| `partials/components/` | Shared stuff like filters, sort headers, empty states, and the typing race |
| `partials/sections/` | Portable page sections, targeted by swaps |
| `widgets/` | Form widget templates past Django's defaults |
| `account/`, `allauth/` | Overrides for allauth's pages, emails, and elements |

#### HTMX patterns
- Modals - a button does `hx-get` with `hx-target="#page-dialog"`, and the `<dialog>` in `partials/components/page_dialog.html` opens itself after the swap
- Saving a modal - On success, return the relevant row partial and `htmx_swap()` retargets the response to the relevant table, with a `close-dialog` trigger to shut the dialog. On error, re-renders the modal in place with error display
- Bulk delete - `bulk_deleted()` returns an empty response with a `rows-deleted` trigger, and `bulk_select.js` removes the rows
- Toasts - views just call Django's `messages.success()` etc, which get picked up by `HtmxMessagesMiddleware` into an `HX-Trigger` header and shown by `toasts.js`
- CSRF - set once for all HTMX requests through `hx-headers` on `<body>`

#### Static files
| File | Contents |
| --- | --- |
| `tail_in.css` | Tailwind input + custom CSS. Edit this one |
| `site.css` | Tailwind output, don't edit |
| `basecoat.min.js` | Copied from `node_modules` by `npm run build:js`, don't edit |
| `htmx-2.0.1.min.js` | Vendored HTMX |
| `toasts.js` | Show toasts from Django `messages` |
| `step_form.js` | Multi-step modal forms, call `initStepForm()` in the modal template |
| `tables.js` | Shared table helpers + `initTableSort()` |
| `table_filter.js` | Type chips + search on the inventory pages |
| `filter_card.js` | Combobox filters + search on the stock pages |
| `bulk_select.js` | Row checkboxes + bulk action bar |
| `typing_race.js` | WPM test typing race thing on the dashboard |
| `words/words.txt` | Word list for the WPM test |

Page-specific scripts go in that page's `page_js` block. When adding a new Tailwind class to a template, rebuild `site.css` with `just build-css`.
