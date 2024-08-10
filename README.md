# keybort
Track personal mechanical keyboard collection and parts inventory. Users can write custom parts lists or use prefilled part info.

#### Tech
- Django 5.0 
- PostgreSQL 16 (AWS RDS)
- Frontend through Django template engine, with some extra stuff:
    - htmx 2.0.1
    - AdminKit 3.4.0/Bootstrap 5.3.2
    - [django allauth](https://docs.allauth.org/en/latest/)
    - [datatables](https://datatables.net/)
- Serverless through [zappa](https://github.com/zappa/Zappa) (AWS Lambda)

#### Feature/docs wishlist
- Stock prebuilt section for stuff like Logitech/Razer/Corsair, Keychron's prebuilts, etc
- Compatibility checker similar to pcpartpicker
- Easy way for admin users to upload/update canned parts, maybe automation?
- Document all the polymorphic key nonsense happening (probably just do a table diagram for the boards app)