# Command for the AdventureBoard

Run these with the following command: `mask [command name]` (ex. `mask run board`).

Make sure you have [mask](https://github.com/jacobdeichert/mask) installed.

## run

Commands for running the development environment.

### board

> Run the board (backend)

```sh
echo "Running the board..."
cd board
python main.py
```

### frontend

> Run the frontend

```sh
echo "Running the frontend..."
cd frontend
npx quasar dev
```