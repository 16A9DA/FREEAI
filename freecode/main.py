import typer

app = typer.Typer(help="freeai local AI coding assistant.")


@app.callback(invoke_without_command=True)
def main():
    typer.echo("freeai skeleton installed. Welcome screen coming soon.")
