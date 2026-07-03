# keybort
Track personal mechanical keyboard collection and parts inventory. Users can write custom parts lists or use prefilled part info.

#### Tech
- Django + Postgres
- Frontend through Django template engine, with some extra stuff:
    - htmx 2.0.1
    - [Basecoat UI](https://basecoatui.com) + Tailwind
    - [django allauth](https://docs.allauth.org/en/latest/)
    - [datatables](https://datatables.net/)
- Will run via docker + nginx on my homelab server

#### To do
- [ ] Finish porting from Bootstrap to Basecoat + Tailwind - including allauth template component usage
- [ ] Import functions for stock stuff
- [ ] Tests

#### Feature/docs wishlist
- Stock prebuilt section for stuff like Logitech/Razer/Corsair, Keychron's prebuilts, etc
- Compatibility checker similar to pcpartpicker
- Easy way for admin users to upload/update canned parts, maybe automation?
- Document all the polymorphic key nonsense happening (probably just do a table diagram for the boards app)
