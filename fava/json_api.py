"""JSON API.

This module contains the url endpoints of the JSON API that is used by the web
interface for asynchronous functionality.
"""

import os
from os import path
import functools
import shutil

from flask import Blueprint, jsonify, g, request

from fava.serialisation import deserialise, serialise
from fava.core.file import save_entry_slice
from fava.core.helpers import FavaAPIException
from fava.core.misc import align

json_api = Blueprint("json_api", __name__)  # pylint: disable=invalid-name


def api_endpoint(func):
    """Register an endpoint."""

    @json_api.route("/{}/".format(func.__name__), methods=["GET"])
    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        return jsonify({"success": True, "data": func(*args, **kwargs)})

    return _wrapper


def json_response(func):
    """Jsonify the response."""

    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        json_data = func(*args, **kwargs)
        if "success" not in json_data:
            json_data["success"] = True
        return jsonify(json_data)

    return _wrapper


def json_request(func):
    """Check existence and load the JSON payload of the request."""

    @functools.wraps(func)
    def _wrapper():
        request_data = request.get_json()
        if request_data is None:
            raise FavaAPIException("Invalid JSON request.")
        return func(request_data)

    return _wrapper


@json_api.errorhandler(FavaAPIException)
@json_response
def _json_api_exception(error):
    return {"success": False, "error": error.message}


@json_api.errorhandler(OSError)
@json_response
def _json_api_oserror(error):
    return {"success": False, "error": error.strerror}


@api_endpoint
def changed():
    """Check for file changes."""
    return g.ledger.changed()


@api_endpoint
def errors():
    """Number of errors."""
    return len(g.ledger.errors)


@api_endpoint
def payee_accounts():
    """Rank accounts for the given payee."""
    return g.ledger.attributes.payee_accounts(request.args.get("payee"))


@api_endpoint
def extract():
    """Extract entries using the ingest framework."""
    entries = g.ledger.ingest.extract(
        request.args.get("filename"), request.args.get("importer")
    )
    return list(map(serialise, entries))


@api_endpoint
def move():
    """Move a file."""
    if not g.ledger.options["documents"]:
        raise FavaAPIException("You need to set a documents folder.")

    account = request.args.get("account")
    new_name = request.args.get("newName")
    filename = request.args.get("filename")

    new_path = filepath_in_document_folder(
        g.ledger.options["documents"][0], account, new_name
    )

    if not path.isfile(filename):
        raise FavaAPIException("Not a file: '{}'".format(filename))

    if path.exists(new_path):
        raise FavaAPIException("Target file exists: '{}'".format(new_path))

    if not path.exists(path.dirname(new_path)):
        os.makedirs(path.dirname(new_path), exist_ok=True)

    shutil.move(filename, new_path)

    return "Moved {} to {}.".format(filename, new_path)


@api_endpoint
def payee_transaction():
    """Last transaction for the given payee."""
    entry = g.ledger.attributes.payee_transaction(request.args.get("payee"))
    return serialise(entry)


@json_api.route("/source/", methods=["PUT"])
@json_request
@json_response
def source(request_data):
    """Write one of the source files."""
    if request_data.get("file_path"):
        sha256sum = g.ledger.file.set_source(
            request_data.get("file_path"),
            request_data.get("source"),
            request_data.get("sha256sum"),
        )
    else:
        entry = g.ledger.get_entry(request_data.get("entry_hash"))
        sha256sum = save_entry_slice(
            entry, request_data.get("source"), request_data.get("sha256sum")
        )
    return {"sha256sum": sha256sum}


@json_api.route("/format-source/", methods=["POST"])
@json_request
@json_response
def format_source(request_data):
    """Format beancount file."""
    aligned = align(request_data["source"], g.ledger.fava_options)
    return {"payload": aligned}


def filepath_in_document_folder(documents_folder, account, filename):
    """File path for a document in the folder for an account.

    Args:
        documents_folder: The documents folder.
        account: The account to choose the subfolder for.
        filename: The filename of the document.

    Returns:
        The path that the document should be saved at.
    """

    if documents_folder not in g.ledger.options["documents"]:
        raise FavaAPIException(
            "Not a documents folder: {}.".format(documents_folder)
        )

    if account not in g.ledger.attributes.accounts:
        raise FavaAPIException("Not a valid account: '{}'".format(account))

    for sep in os.sep, os.altsep:
        if sep:
            filename = filename.replace(sep, " ")

    return path.normpath(
        path.join(
            path.dirname(g.ledger.beancount_file_path),
            documents_folder,
            *account.split(":"),
            filename
        )
    )


@json_api.route("/add-document/", methods=["PUT"])
@json_response
def add_document():
    """Upload a document."""
    if not g.ledger.options["documents"]:
        raise FavaAPIException("You need to set a documents folder.")

    upload = request.files["file"]

    if not upload:
        raise FavaAPIException("No file uploaded.")

    filepath = filepath_in_document_folder(
        request.form["folder"],
        request.form["account"],
        request.form["filename"],
    )
    directory, filename = path.split(filepath)

    if path.exists(filepath):
        raise FavaAPIException("{} already exists.".format(filepath))

    if not path.exists(directory):
        os.makedirs(directory, exist_ok=True)

    upload.save(filepath)

    if request.form.get("hash"):
        g.ledger.file.insert_metadata(
            request.form["hash"], "document", filename
        )
    return {"message": "Uploaded to {}".format(filepath)}


@json_api.route("/add-entries/", methods=["PUT"])
@json_request
@json_response
def add_entries(request_data):
    """Add multiple entries."""
    try:
        entries = [deserialise(entry) for entry in request_data["entries"]]
    except KeyError as error:
        raise FavaAPIException("KeyError: {}".format(str(error)))

    g.ledger.file.insert_entries(entries)

    return {"message": "Stored {} entries.".format(len(entries))}
