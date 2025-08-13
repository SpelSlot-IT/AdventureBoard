# Adventure Board
See http://shepherd-itsec.com/dnd/ for a live demo


## Online usage
- See the [HELP](http://shepherd-itsec.com/dnd/cgi-bin/app.cgi/help) section of the live demo in the top right for usage help.
- See the documentation for [REST API](http://shepherd-itsec.com/dnd/cgi-bin/app.cgi/openapi/docs) for developer help.

## Offline usage
1. Clone the repository.
2. Set up a database. Currently using MySQL, but other flavors are also supported.
3. Navigate to the `cgi-bin` directory of the repository.
4. Please set up a venv and run `pip install -r requirements.txt` to install dependencies.
5. Create a `config.local.json` file based on `config.example`
6. Run `python app.py` to run a local flask server

## Further information
Trello: https://trello.com/b/uaEDW0Ks/adventure-board-spelslot