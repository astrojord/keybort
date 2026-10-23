# keybort
Track personal mechanical keyboard collection and parts inventory. Users can write custom parts lists or use prefilled part info.

#### Tech
- Django + Postgres
- Frontend through Django template engine, with some extra stuff:
    - htmx 2.0.1
    - [Basecoat UI](https://basecoatui.com) + Tailwind
    - [django allauth](https://docs.allauth.org/en/latest/)
- Will run via docker + nginx on my homelab server

#### To do
- [ ] Stock part setup, including handler for CSV upload
- [ ] UI/UX improvements - brainstorm
  - [ ] Mobile tables are way too long - switch to some sort of stacked card/collapsible approach perhaps
  - [ ] Overall, just needs more juice/visual interest
- [ ] Use comboboxes for custom parts forms to allow a set of common brands/names etc, like the Gaterons, GMKs, SPs of the world
- [ ] Break out part-specific table headers for specific part inventory - eg the switches table should have the stem type and actuation force etc etc
- [ ] Typing minigame on dashboard?
- [ ] Collection stats type stuff on dashboard - layout breakdown, most used switch, most used keycap brand, etc
- [ ] allauth social account stuff, or at the very least, email verification

#### Feature/docs wishlist
- Stock prebuilt section for stuff like Logitech/Razer/Corsair, Keychron's prebuilts, etc
- Compatibility checker similar to pcpartpicker
- Easy way for admin users to upload/update canned parts, maybe automation?
- Document all the polymorphic key nonsense happening (probably just do a table diagram for the boards app)
