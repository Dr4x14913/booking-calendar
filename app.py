from flask import Flask, send_from_directory, render_template
import json
from pathlib import Path

app = Flask(__name__)

@app.route('/')
def serve_index():
    booked_dates = get_booked_dates()
    return render_template('index.html', bookedDatesJson=booked_dates)

def get_booked_dates():
    json_file = "/app/booked_dates.json"
    if not Path(json_file).exists():
        with open(json_file, "w") as f:
            json.dump([], f) 

    with open(json_file, "r") as f:
        return json.load(f) 

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

