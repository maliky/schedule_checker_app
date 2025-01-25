from flask import Flask, request, render_template, redirect, url_for, send_file
import os
import pandas as pd
import altair as alt
import sys
from pathlib import Path

from class_schedule.visualisation import create_visualizations
from class_schedule.helper import process_schedule
import logging
from dotenv import load_dotenv

load_dotenv()  # Load variables from .env

app = Flask(__name__, static_folder="static")
# app.config['UPLOAD_FOLDER'] = "self./uploads"
app.config["PROCESSED_FOLDER"] = "./processed"

app.config["ENV"] = os.getenv("FLASK_ENV", "production")  # Default to production
app.config["DEBUG"] = app.config["ENV"] == "development"

logging.basicConfig(filename="app.log", level=logging.INFO)

# Add the current working directory to the Python path as a fallback
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.append(str(Path(__file__).resolve().parent))
    sys.path.append(str(Path(__file__).resolve().parent / "class_schedule"))


################
# ROUTE VIEWS  #
################
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", titre="Upload Your Schedule")


@app.route("/upload", methods=["POST"])
def upload_file():
    """Handles the file upload and triggers processing."""
    try:
        fname = request.files.get("file")
        sheet_name = request.form.get("sheet", "GENERAL SCHEDULE")

        if not fname:
            return "No file uploaded", 400

        # Validate file type (e.g., ensure it's Excel)
        if not fname.filename.endswith((".xlsx", ".xls")):
            return "Invalid file type. Please upload an Excel file.", 400

        # Load into pandas
        processed_df = process_schedule(fname, sheet_name)

        # Optionally save the processed file
        processed_path = os.path.join(app.config["PROCESSED_FOLDER"], "processed_schedule.xlsx")

        processed_df.to_excel(processed_path, index=False)

        # Generate the charts (and save them as HTML in templates or static)

        create_visualizations(processed_df, dout="templates")

        # Return a simple text response for the fetch() call
        # (The front-end will interpret this as success and display a link)
        return "File successfully processed!", 200

    except Exception as e:
        logging.exception(f"An error occured: {str(e)}")


@app.route("/view_instructor_chart")
def view_instructor_chart():
    # Either return a template that embeds instructor_final_chart.html
    return render_template("instructor_final_chart.html")


@app.route("/view_room_chart")
def view_room_chart():
    # Either return a template that embeds room_final_chart.html
    return render_template("room_final_chart.html")


@app.route("/download_processed", methods=["GET"])
def download_processed_file():
    """
    Route to download the processed schedule file.
    """
    processed_path = os.path.join(app.config["PROCESSED_FOLDER"], "processed_schedule.xlsx")

    if not os.path.exists(processed_path):
        return (
            "No processed file available. Please upload and process a schedule first.",
            404,
        )

    return send_file(
        processed_path, as_attachment=True, download_name="processed_schedule.xlsx"
    )


if __name__ == "__main__":
    # app.run(debug=True)
    app.run(host="0.0.0.0", port=9090)
