# Adventure Board
See http://shepherd-itsec.com/dnd/ for a live demoW
- See the [HELP](http://shepherd-itsec.com/dnd/cgi-bin/app.cgi/help) section of the live demo in the top right for usage help.
- See the documentation of the [REST API](http://shepherd-itsec.com/dnd/cgi-bin/app.cgi/openapi/docs) for developer help.

# Hosting
## Hosting raw
This method is recommended if you want to develop and locally test the app with minimal setup.
1. Clone the repository.
2. Set up a database. Currently using MySQL, but other flavors are also supported.
3. Navigate to the `board` directory of the repository.
4. Please set up a venv and run `pip install -r requirements.txt` to install dependencies.
5. Create a `config.local.json` file in the `app/config` directory based on [`config.example`](board/app/config/config.example).
6. Run `python main.py` to run a local flask server.

## Hosting with docker (Developer)
This method is recommended if you want to develop and locally test the app under real conditions.
1. Clone the repository.
2. Navigate to the `board` directory of the repository.
3. Create a `config.dev.json` file in the `app/config` directory based on [`config.example`](board/app/config/config.example).
3. Run `docker compose up --build`

## Hosting with docker (User)
This method is recommended if you want to run the app while keeping up-to-date without rebuilding.

0. If you want to, you can copy the examples by running the following commands:
```bash
wget https://raw.githubusercontent.com/Shepherd-ITSec/AdventureBoard/refs/heads/main/docker-compose.yaml
wget https://raw.githubusercontent.com/Shepherd-ITSec/AdventureBoard/refs/heads/main/nginx.conf
wget https://raw.githubusercontent.com/Shepherd-ITSec/AdventureBoard/refs/heads/main/config.example
```
1. Create a docker-compose file using the `ghcr.io/shepherd-itsec/adventureboard:latest` image, see [`docker-compose.yaml`](docker-compose.yaml)
2. Create a nginx config to your liking, see [`nginx.conf`](nginx.conf)
3. Create a `config.json`, see [`config.example`](config.example)
4. Run `docker compose up --build`

# Configuration
The configuration depends on the hosting method. Please always see the corresponding examples. After copying the example the following variables **need** to be set:
- `APP`: `SECRET_KEY`
- `DB`: `USER`,`PASSWORD` and `NAME`
- `GOOGLE`: `CLIENT_ID` and `CLIENT_SECRET` (You can find these in you [OAuth 2.0 google developer account](https://support.google.com/googleapi/answer/6158849?hl=en&ref_topic=7013279&sjid=14747871361252941722-EU))
- `API_SPEC_OPTIONS`: `servers` (if it differs form the standard)
Please see that `DB`: `flavor` only supports `mysql+pymysql` and `postgresql+psycopg` as these are the only preinstalled drivers. When installing the required drivers all SQAlchemy flavors are supported.

# Frontend development

The frontend is written in VueJS with the Quasar framework. To get started:

```shell
cd frontend
npm clean-install
npx quasar dev
```

You can fake logging in by stealing the cookie from https://signup.spelslot.nl/, and using the developer console to set `document.cookie = 'session=xxx'`.


# Further information
Trello: https://trello.com/b/uaEDW0Ks/adventure-board-spelslot
