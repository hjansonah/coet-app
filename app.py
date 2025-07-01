import os
import psycopg2
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def get_reviewed_ids():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT "ID" FROM "coets_android_appended" WHERE last_reviewed IS NOT NULL ORDER BY last_reviewed')
    ids = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()
    return ids

@app.route("/")
def index():
    conn = get_connection()
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

    conn = get_connection()
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

    conn = get_connection()
    cur = conn.cursor()
    cur.execute('UPDATE "coets_android_appended" SET "Still valid" = %s WHERE "ID" = %s', (value, record_id))
    conn.commit()
    cur.close()
    conn.close()

    return jsonify(success=True)

@app.route("/next/<int:index>")
def next_record(index):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT "ID" FROM "coets_android_appended" WHERE last_reviewed IS NULL ORDER BY "ID" LIMIT 1')
    next_unreviewed = cur.fetchone()

    if not next_unreviewed:
        cur.close()
        conn.close()
        return "No more unreviewed records", 404

    next_id = next_unreviewed[0]

    cur.execute('UPDATE "coets_android_appended" SET last_reviewed = CURRENT_TIMESTAMP WHERE "ID" = %s', (next_id,))
    conn.commit()

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
    app.run(host="0.0.0.0", port=8080)
