# Adventure Board
See http://shepherd-itsec.com/dnd/ for a live demoW
- See the documentation of the [REST API](https://signup.spelslot.nl/openapi/docs) for developer help.

# Backend Hosting
## Hosting raw (Recommended)
This method is recommended if you want to develop and locally test the app with minimal setup.
1. Clone the repository.
2. Set up a database. Currently using MySQL, but other flavors are also supported. (Or use the mock setup via `bash backend/setup_mock_db.sh`)
3. Navigate to the `backend` directory of the repository.
4. Install [UV](https://docs.astral.sh/uv/), then run `uv venv` followed by `uv sync`.
5. Create a `config.local.json` file in the `app/config` directory based on [`config.example`](backend/app/config/config.example). (For more information on this see **Configuration** later on in this document.)
6. Run the local flask server: `uv run python main.py`.

## Hosting with docker (Develop)
This method is recommended if you want to develop and locally test the app under real conditions.
1. Clone the repository.
2. Navigate to the `backend` directory of the repository.
3. Create a `config.dev.json` file in the `app/config` directory based on [`config.example`](backend/app/config/config.example).
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



## Configuration
The configuration depends on the hosting method. Please always see the corresponding examples. After copying the example the following variables **need** to be set:
- `APP`: `SECRET_KEY`
- `DB`: `USER`,`PASSWORD` and `NAME`
- `GOOGLE`: `CLIENT_ID` and `CLIENT_SECRET` (You can find these in you [OAuth 2.0 google developer account](https://support.google.com/googleapi/answer/6158849?hl=en&ref_topic=7013279&sjid=14747871361252941722-EU))
- `API_SPEC_OPTIONS`: `servers` (if it differs form the standard)
Please see that `DB`: `flavor` only supports `mysql+pymysql` and `postgresql+psycopg` as these are the only preinstalled drivers. When installing the required drivers all SQAlchemy flavors are supported.

# Frontend development

The frontend is written in VueJS with the Quasar framework. 
1. Clone the repository.
2. Navigate to the `frontend` directory of the repository.
3. Install `NodeJS`
4. Install the required packages started: `npm clean-install`
5. Run the frontend: `npx quasar dev`

## Running without local backend
If you want to run without a local backend you can use the oficla websites backend my making the following changes. 

> Note: You can fake logging to the online backend by stealing the cookie from https://signup.spelslot.nl/, and using the developer console to set `document.cookie = 'session=xxx'`.

The server configuration in [`quasar.config.js`](frontend/quasar.config.js) needs to be changed to
```js
devServer: {
      server: {
        type: 'http',
      },
      port: 8080,
      proxy: {
        '/api/': {
          target: 'https://signup.spelslot.nl/', // defines if the api target is the local or remote backend
                     secure: false,
          changeOrigin: true,
        },
      },
      open: true, // opens browser window automatically
    },
```

# Tests
Tests can be run with the following commands

Backend tests (pytest):
```shell
cd backend
uv sync --extra test
uv run pytest
```

Frontend tests (vitest):
```shell
cd frontend
npm ci
npm test
```

# Further information
Trello: https://trello.com/b/uaEDW0Ks/adventure-board-spelslot
