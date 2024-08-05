# keybort
Track personal mechanical keyboard collection and parts inventory. Users can write custom parts lists or use prefilled part info.

#### Tech
- Django 5.0 
- PostgreSQL 16 (AWS RDS)
- Frontend through Django template engine, styled by AdminKit 3.4.0/Bootstrap 5.3.2
- Serverless through zappa + AWS Lambda

#### Feature/docs wishlist
- Compatibility checker similar to pcpartpicker
- Easy way for admin users to upload/update canned parts, maybe automation?
- Document all the polymorphic key nonsense happening (probably just do a table diagram for the boards app)