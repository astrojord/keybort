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
2. `docker compose up --build`
3. `just migrate` or without just, `docker compose exec app python manage.py migrate` - other helpful functions are in the justfile

Test with the Django runner, `just test` or `docker compose exec app python manage.py test`. GitHub Actions runs ruff and testing with coverage output.

#### To do
- [ ] UI/UX improvements - brainstorm
  - [ ] Mobile tables are way too long - switch to some sort of stacked card/collapsible approach perhaps
  - [ ] Overall, just needs more juice/visual interest
- [ ] allauth social account stuff
- [ ] Set up [Resend](https://resend.com/home) for email stuff on the deployed version

#### Credits
- The typing race word list (`keybort/static/words/words.txt`) combines the no-swears short and medium lists from [google-10000-english](https://github.com/first20hours/google-10000-english), filtered against the [ENABLE](https://github.com/dolph/dictionary) dictionary and the [naughty-words](https://www.npmjs.com/package/naughty-words) list (CC-BY-4.0), then reviewed by hand

#### Feature/docs wishlist
- Compatibility checker similar to pcpartpicker
- TBD
