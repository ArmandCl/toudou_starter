import logging

import click
import uuid

from datetime import datetime

import toudou.models as models
import toudou.services as services
from flask import render_template, Flask, request,Response, Blueprint, flash, redirect, url_for, abort
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField
from wtforms.validators import DataRequired


import os

secret_key = os.getenv('TOUDOU_FLASK_SECRET_KEY')

@click.group()
def cli():
    pass


@cli.command()
def init_db():
    models.init_db()


@cli.command()
@click.option("-t", "--task", prompt="Your task", help="The task to remember.")
@click.option("-d", "--due", type=click.DateTime(), default=None, help="Due date of the task.")
def create(task: str, due: datetime):
    models.create_todo(task, due=due)


@cli.command()
@click.option("--id", required=True, type=click.UUID, help="Todo's id.")
def get(id: uuid.UUID):
    click.echo(models.get_todo(id))


@cli.command()
@click.option("--as-csv", is_flag=True, help="Ouput a CSV string.")
def get_all(as_csv: bool):
    if as_csv:
        click.echo(services.export_to_csv())
    else:
        click.echo(models.get_all_todos())


@cli.command()
@click.argument("csv_file", type=click.File("r"))
def import_csv(csv_file):
    services.import_from_csv(csv_file)


@cli.command()
@click.option("--id", required=True, type=click.UUID, help="Todo's id.")
@click.option("-c", "--complete", required=True, type=click.BOOL, help="Todo is done or not.")
@click.option("-t", "--task", prompt="Your task", help="The task to remember.")
@click.option("-d", "--due", type=click.DateTime(), default=None, help="Due date of the task.")
def update(id: uuid.UUID, complete: bool, task: str, due: datetime):
    models.update_todo(id, task, complete, due)


@cli.command()
@click.option("--id", required=True, type=click.UUID, help="Todo's id.")
def delete(id: uuid.UUID):
    models.delete_todo(id)

@cli.command()
def affiche_table():
    models.display_tables()








web_ui =Blueprint("web_ui",__name__, url_prefix="/")


class InsertTodoForm(FlaskForm):
    insert_task = StringField('Task', validators=[DataRequired()])
    insert_date = StringField('Date')
    submit = SubmitField('Submit')

class UpdateTodoForm(FlaskForm):
    ID_update = StringField('ID_update', validators=[DataRequired()], render_kw={'type': 'hidden'})
    update_task = StringField('Task')
    complete = BooleanField('Complete')
    update_date = StringField('Date')
    submit = SubmitField('Submit')



def create_app():
    app = Flask(__name__)
    from toudou.views import web_ui
    app.register_blueprint(web_ui)
    app.secret_key = secret_key

    return app


@web_ui.route('/')
def accueil():
    models.init_db()

    insert_form = InsertTodoForm()
    update_form = UpdateTodoForm()

    tasks = models.get_all_todos()
    return render_template("index.html", tasks=tasks, insert_form=insert_form, update_form=update_form)


@web_ui.route('/insert', methods=["GET", "POST"])
def insert_task():
    insert_form = InsertTodoForm()
    update_form = UpdateTodoForm()
    message = ""
    if insert_form.validate_on_submit():
        task = insert_form.insert_task.data
        due = datetime.strptime(insert_form.insert_date.data, "%Y-%m-%d") if insert_form.insert_date.data else None

        if models.create_todo(task, due=due):
            message = "Task created successfully"
            insert_form = InsertTodoForm()
        else:
            message = "Failed to create task"

    tasks = models.get_all_todos()
    return render_template("index.html", tasks=tasks, message=message, insert_form=insert_form, update_form=update_form)


@web_ui.route('/update', methods=["GET", "POST"])
def update_task():
    message = ""
    insert_form = InsertTodoForm()
    update_form = UpdateTodoForm()
    if update_form.validate_on_submit():
        id_update = uuid.UUID(update_form.ID_update.data)
        todo_to_update = models.get_todo(id_update)

        new_task = todo_to_update.task if update_form.update_task.data == "" else update_form.update_task.data
        new_complete = update_form.complete.data
        new_due = datetime.strptime(update_form.update_date.data, "%Y-%m-%d") if update_form.update_date.data else todo_to_update.due

        models.update_todo(id_update, new_task, new_complete, new_due)
        message = "Task updated successfully"
        update_form = UpdateTodoForm()
    else :
        message = "Failed to update the task"

    tasks = models.get_all_todos()
    return render_template("index.html", tasks=tasks, message=message, insert_form=insert_form, update_form=update_form)



@web_ui.route('/delete', methods=["GET", "POST"])
def delete_task():
    message = ""
    update_form = UpdateTodoForm()
    insert_form = InsertTodoForm()
    if request.method == 'POST':
        id_delete = request.form['id']
        models.delete_todo(id_delete)
        message = "Task deleted successfully"

    tasks = models.get_all_todos()
    return render_template("index.html", tasks=tasks, message=message, insert_form=insert_form,update_form=update_form)

@web_ui.route('/exportcsv', methods=["GET", "POST"])
def export_csv():

    tasks = models.get_all_todos()
    export = services.export_to_csv()
    if export == 0:
        message = "Export successful. Data written to /db/db.csv"
    else:
        message = "No data to export !"
    return render_template("index.html", tasks=tasks, message=message)

@web_ui.route('/importcsv', methods=["GET", "POST"])
def import_csv():
    # Get the list of tasks before import
    tasks_before_import = models.get_all_todos()

    # Check if a CSV file has been provided in the request
    if 'csv_file' not in request.files:
        message = "No CSV file provided."
        return render_template("index.html", tasks=tasks_before_import, message=message)

    csv_file = request.files['csv_file']

    # Check if the file has a proper name and extension
    if csv_file.filename == '' or not csv_file.filename.endswith('.csv'):
        message = "Invalid CSV file."
        return render_template("index.html", tasks=tasks_before_import, message=message)

    # Call the import function with the CSV file
    import_result = services.import_from_csv(csv_file)

    # Get the list of tasks after import
    tasks_after_import = models.get_all_todos()

    if import_result == 0:
        message = "Import successful."
    elif import_result == 1:
        message = "No data imported. The CSV file is empty."
    elif import_result == 2:
        message = "Error reading the CSV file."
    else:
        message = "An unspecified error occurred during import. (It's probably due to the date !)"

    # Use the list of tasks before import if an error occurred
    tasks = tasks_after_import if import_result == 0 else tasks_before_import

    return render_template("index.html", tasks=tasks, message=message)

@web_ui.errorhandler(500)
def handle_internal_error(error):
    logging.exception(error)
    return redirect(url_for(".accueil"))

@web_ui.errorhandler(404)
def handle_internal_error(error):
    logging.exception(error)
    return redirect(url_for(".accueil"))
