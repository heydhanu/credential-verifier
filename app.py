import hashlib, json, io, os
from flask import Flask, request, redirect, send_file, render_template_string
import qrcode

app = Flask(__name__)
LEDGER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ledger.json")

def load():
    return json.load(open(LEDGER)) if os.path.exists(LEDGER) else []

def save(l):
    json.dump(l, open(LEDGER, "w"), indent=2)

def core(b):
    return {k: v for k, v in b.items() if k != "hash"}

def h(b):
    return hashlib.sha256(json.dumps(core(b), sort_keys=True).encode()).hexdigest()

BASE = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Credential Verifier</title>
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: "Segoe UI", Arial, sans-serif;
    background: #f1f4fa;
    color: #1f2937;
  }
  nav {
    background: #1e3a8a;
    padding: 14px 24px;
    display: flex;
    gap: 24px;
    align-items: center;
  }
  nav .brand { color: white; font-weight: 700; font-size: 18px; margin-right: auto; }
  nav a { color: #dbe4ff; text-decoration: none; font-size: 14px; }
  nav a:hover { color: white; }
  main { max-width: 760px; margin: 32px auto; padding: 0 16px; }
  .card {
    background: white;
    border-radius: 14px;
    padding: 28px;
    box-shadow: 0 4px 18px rgba(30, 58, 138, 0.08);
    margin-bottom: 20px;
  }
  h1 { margin: 0 0 6px 0; font-size: 26px; }
  .sub { color: #6b7280; margin: 0 0 20px 0; font-size: 14px; }
  label { display: block; font-size: 13px; font-weight: 600; margin: 14px 0 6px; }
  input {
    width: 100%;
    padding: 11px 12px;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    font-size: 15px;
  }
  input:focus { outline: none; border-color: #2563eb; box-shadow: 0 0 0 3px #dbeafe; }
  .btn {
    display: inline-block;
    background: #2563eb;
    color: white;
    border: none;
    padding: 11px 20px;
    border-radius: 8px;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    text-decoration: none;
    margin-top: 18px;
  }
  .btn:hover { background: #1d4ed8; }
  .btn.alt { background: #e5e7eb; color: #1f2937; margin-left: 8px; }
  .btn.alt:hover { background: #d1d5db; }
  .field { margin: 12px 0; }
  .field span { display: block; font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; }
  .field div { font-size: 17px; font-weight: 600; }
  code {
    display: block;
    background: #f3f4f6;
    padding: 8px 10px;
    border-radius: 6px;
    font-size: 12px;
    word-break: break-all;
    margin-top: 4px;
  }
  .qr { text-align: center; }
  .qr img { border: 1px solid #e5e7eb; border-radius: 10px; padding: 8px; background: white; }
  table { width: 100%; border-collapse: collapse; font-size: 14px; }
  th { text-align: left; background: #eef2ff; padding: 10px; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
  td { padding: 10px; border-bottom: 1px solid #eef0f4; }
  tr:hover td { background: #fafbff; }
  td a { color: #2563eb; text-decoration: none; font-weight: 600; }
  .scroll { overflow-x: auto; }
  .result { text-align: center; }
  .badge {
    display: inline-block;
    font-size: 30px;
    font-weight: 800;
    padding: 12px 34px;
    border-radius: 50px;
    margin: 10px 0 18px;
  }
  .badge.VALID { background: #dcfce7; color: #166534; }
  .badge.TAMPERED { background: #fee2e2; color: #991b1b; }
  .badge.NOTFOUND { background: #e5e7eb; color: #374151; }
</style>
</head>
<body>
<nav>
  <span class="brand">Credential Verifier</span>
  <a href="/">Issue</a>
  <a href="/credentials">All credentials</a>
</nav>
<main>{{ body|safe }}</main>
</body>
</html>
"""

HOME = """
<div class="card">
  <h1>Issue a credential</h1>
  <p class="sub">Create a tamper-evident digital certificate secured with SHA-256 hash chaining.</p>
  <form method="post" action="/issue">
    <label>Recipient name</label>
    <input name="name" placeholder="e.g. Aisyah Rahman" required>
    <label>Course</label>
    <input name="course" placeholder="e.g. Cloud Computing Fundamentals" required>
    <label>Date</label>
    <input name="date" type="date" required>
    <button class="btn">Issue credential</button>
    <a class="btn alt" href="/credentials">View all</a>
  </form>
</div>
"""

CRED = """
<div class="card">
  <h1>Credential #{{ b.id }}</h1>
  <p class="sub">Issued and recorded in the hash chain.</p>
  <div class="field"><span>Name</span><div>{{ b.name }}</div></div>
  <div class="field"><span>Course</span><div>{{ b.course }}</div></div>
  <div class="field"><span>Date</span><div>{{ b.date }}</div></div>
  <div class="field"><span>Hash</span><code>{{ b.hash }}</code></div>
  <div class="field"><span>Previous hash</span><code>{{ b.prev_hash }}</code></div>
</div>
<div class="card qr">
  <p class="sub">Scan to verify</p>
  <img src="/qr/{{ b.id }}" width="200">
  <br>
  <a class="btn" href="/verify?id={{ b.id }}&hash={{ b.hash }}">Verify this credential</a>
  <a class="btn alt" href="/credentials">All credentials</a>
</div>
"""

RESULT = """
<div class="card result">
  <p class="sub">Verification result</p>
  <div class="badge {{ status.replace(' ', '') }}">{{ status }}</div>
  <p>{{ msg }}</p>
  <a class="btn" href="/">Home</a>
  <a class="btn alt" href="/credentials">All credentials</a>
</div>
"""

LIST = """
<div class="card">
  <h1>All credentials</h1>
  <p class="sub">{{ ledger|length }} record(s) in the chain.</p>
  <div class="scroll">
  <table>
    <tr><th>ID</th><th>Name</th><th>Course</th><th>Date</th><th>Hash</th><th></th></tr>
    {% for b in ledger %}
    <tr>
      <td>{{ b.id }}</td>
      <td>{{ b.name }}</td>
      <td>{{ b.course }}</td>
      <td>{{ b.date }}</td>
      <td>{{ b.hash[:10] }}...</td>
      <td>
        <a href="/credential/{{ b.id }}">View</a> |
        <a href="/verify?id={{ b.id }}&hash={{ b.hash }}">Verify</a>
      </td>
    </tr>
    {% else %}
    <tr><td colspan="6">No credentials issued yet.</td></tr>
    {% endfor %}
  </table>
  </div>
  <a class="btn" href="/">Issue another</a>
</div>
"""

def page(template, **ctx):
    body = render_template_string(template, **ctx)
    return render_template_string(BASE, body=body)

@app.route("/")
def index():
    return page(HOME)

@app.route("/issue", methods=["POST"])
def issue():
    l = load()
    b = {"id": len(l) + 1, "name": request.form["name"], "course": request.form["course"],
         "date": request.form["date"], "prev_hash": l[-1]["hash"] if l else "0" * 64}
    b["hash"] = h(b)
    l.append(b)
    save(l)
    return redirect(f"/credential/{b['id']}")

@app.route("/credential/<int:cid>")
def credential(cid):
    l = load()
    if not 1 <= cid <= len(l):
        return page(RESULT, status="NOT FOUND", msg="No such credential.")
    return page(CRED, b=l[cid - 1])

@app.route("/credentials")
def credentials():
    return page(LIST, ledger=load())

@app.route("/qr/<int:cid>")
def qr(cid):
    b = load()[cid - 1]
    url = f"{request.host_url}verify?id={b['id']}&hash={b['hash']}"
    buf = io.BytesIO()
    qrcode.make(url).save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")

@app.route("/verify")
def verify():
    l = load()
    cid = int(request.args.get("id", 0))
    given = request.args.get("hash", "")
    if not 1 <= cid <= len(l):
        return page(RESULT, status="NOT FOUND", msg="No such credential.")
    ok = True
    for i, b in enumerate(l[:cid]):
        if h(b) != b["hash"]:
            ok = False
        if i > 0 and b["prev_hash"] != l[i - 1]["hash"]:
            ok = False
    if l[cid - 1]["hash"] != given:
        ok = False
    b = l[cid - 1]
    return page(
        RESULT,
        status="VALID" if ok else "TAMPERED",
        msg=f"{b['name']} | {b['course']} | {b['date']}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)