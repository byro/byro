# Testing byro with Docker

## First light
Start the show using `docker-compose up`.

It should complain about outstanding migrations that need to run.
This is fine, let's fix this by running the following in a second terminal window:

`docker exec src_web_1 python3 manage.py migrate`

Now we're just missing a superuser with which to log into byro.
To create one run the following command:

`docker exec -it src_web_1 python3 manage.py createsuperuser`

You should not be able to go to `http://localhost:8020` and log in.

## Security
Do not run this setup as-is on an exposed machine!
This is for testing purposes only and byro will run in debug mode to allow access from localhost and associated IP addresses.
