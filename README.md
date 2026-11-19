# keybort
Track personal mechanical keyboard collection and parts inventory. Users can write custom parts lists or use prefilled part info.

#### Tech
- Django + Postgres
- Frontend through Django template engine, with some extra stuff:
    - htmx 2.0.1
    - [Basecoat UI](https://basecoatui.com) + Tailwind
    - [django allauth](https://docs.allauth.org/en/latest/)
- Will run via docker + nginx on my homelab server

#### Local setup
1. `cp sample.env env/local.env`, fill in accordingly (`POSTGRES_HOST` should be `db`, the compose service name)
2. `just build-css` and `just build-js` or without just, `npm --prefix keybort run build:css` and `npm --prefix keybort run build:js` - other helpful functions are in the justfile
3. `docker compose up --build`
4. `just migrate` or without just, `docker compose exec app python manage.py migrate`

Test with the Django runner, `just test` or `docker compose exec app python manage.py test`. GitHub Actions runs ruff, djlint, and testing with coverage output.

#### To do
- [ ] Overall, just needs more juice/visual interest
- [ ] allauth social account stuff
- [ ] Set up [Resend](https://resend.com/home) for email stuff on the deployed version
- [ ] Truncate long part names (~50 chars) and longer mod/notes text in the keyboards table

#### Credits
- The typing race word list (`keybort/static/words/words.txt`) combines the no-swears short and medium lists from [google-10000-english](https://github.com/first20hours/google-10000-english), filtered against the [ENABLE](https://github.com/dolph/dictionary) dictionary and the [naughty-words](https://www.npmjs.com/package/naughty-words) list (CC-BY-4.0), then reviewed by hand

#### Feature/docs wishlist
- Compatibility checker similar to pcpartpicker
- TBD
