from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
import psycopg2

app = Flask(__name__)
CORS(app)

DB_PARAMS = {
    "dbname": "postgres",
    "user": "postgres",
    "password": "bouncym2025",
    "host": "127.0.0.1",
    "port": "5432"
}

# Fetch all reviewed record IDs
def get_reviewed_ids():
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    cur.execute('SELECT "ID" FROM "coets_android_appended" WHERE last_reviewed IS NOT NULL ORDER BY last_reviewed')
    ids = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()
    return ids

@app.route("/")
def index():
    # Redirect to the next unreviewed record
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    cur.execute('SELECT "ID" FROM "coets_android_appended" WHERE last_reviewed IS NULL ORDER BY "ID" LIMIT 1')
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return "No unreviewed records found", 404

    return redirect(url_for('next_record', index=0))

@app.route("/record/<int:index>")
def record(index):
    reviewed_ids = get_reviewed_ids()
    if index < 0 or index >= len(reviewed_ids):
        return "Index out of range", 404

    record_id = reviewed_ids[index]

    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    cur.execute('SELECT * FROM "coets_android_appended" WHERE "ID" = %s', (record_id,))
    row = cur.fetchone()
    colnames = [desc[0] for desc in cur.description]
    row_dict = dict(zip(colnames, row))
    cur.close()
    conn.close()

    return render_template("record.html", row=row_dict, index=index, total=len(reviewed_ids))

@app.route("/update", methods=["POST"])
def update():
    index = int(request.form["index"])
    value = request.form["value"] == "True"

    reviewed_ids = get_reviewed_ids()
    if index >= len(reviewed_ids):
        return jsonify(success=False)

    record_id = reviewed_ids[index]

    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    cur.execute('UPDATE "coets_android_appended" SET "Still valid" = %s WHERE "ID" = %s', (value, record_id))
    conn.commit()
    cur.close()
    conn.close()

    return jsonify(success=True)

@app.route("/next/<int:index>")
def next_record(index):
    # Get next unreviewed record
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    cur.execute('SELECT "ID" FROM "coets_android_appended" WHERE last_reviewed IS NULL ORDER BY "ID" LIMIT 1')
    next_unreviewed = cur.fetchone()

    if not next_unreviewed:
        cur.close()
        conn.close()
        return "No more unreviewed records", 404

    next_id = next_unreviewed[0]

    # Mark it reviewed
    cur.execute('UPDATE "coets_android_appended" SET last_reviewed = CURRENT_TIMESTAMP WHERE "ID" = %s', (next_id,))
    conn.commit()

    # Recalculate reviewed list and find index
    cur.execute('SELECT "ID" FROM "coets_android_appended" WHERE last_reviewed IS NOT NULL ORDER BY last_reviewed')
    reviewed_ids = [r[0] for r in cur.fetchall()]
    next_index = reviewed_ids.index(next_id)

    cur.close()
    conn.close()

    return redirect(url_for('record', index=next_index))

@app.route("/previous/<int:index>")
def previous_record(index):
    reviewed_ids = get_reviewed_ids()
    if index <= 0:
        return "No previous record", 404
    return redirect(url_for('record', index=index - 1))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)


