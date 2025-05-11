from flask import Flask, render_template, request, redirect, session, url_for
import random
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "supersecretkey"

admin_email = "admin@worldjackpot.com"
testnutzer = [f"test{i}@worldjackpot.com" for i in range(1, 11)]

sim_jackpot = 10000000
real_jackpot = 10500000
zeige_sim_jackpot = True
scheine = []
freigabe_klasse1 = False
fake_gewinner = []
max_scheine = 10
ziehung = None
letzte_ziehung = None
gewinner_klassen = {}

def get_gewinnerlimits(jackpot_betrag):
    if jackpot_betrag >= 100_000_000:
        return {2: 9, 3: 23, 4: 102, 5: 799}
    elif jackpot_betrag >= 90_000_000:
        return {2: 9, 3: 23, 4: 102, 5: 299}
    elif jackpot_betrag >= 60_000_000:
        return {2: 7, 3: 15, 4: 90, 5: 249}
    elif jackpot_betrag >= 30_000_000:
        return {2: 6, 3: 12, 4: 75, 5: 200}
    else:
        return {2: 4, 3: 10, 4: 50, 5: 150}

def klassifizieren(richtig, world):
    klassen = {
        (5, 2): 1, (5, 1): 2, (5, 0): 3,
        (4, 2): 4, (4, 1): 5, (4, 0): 6,
        (3, 2): 7, (2, 2): 8, (3, 1): 9,
        (3, 0):10, (1, 2):11, (2, 1):12
    }
    return klassen.get((richtig, world))

def ziehung_durchfuehren():
    zahlen_counts = {}
    world_counts = {}
    for s in scheine:
        for z in s["zahlen"]:
            zahlen_counts[z] = zahlen_counts.get(z, 0) + 1
        for w in s["world"]:
            world_counts[w] = world_counts.get(w, 0) + 1
    seltene_zahlen = sorted(range(1, 51), key=lambda x: zahlen_counts.get(x, 0))
    seltene_world = sorted(range(1, 11), key=lambda x: world_counts.get(x, 0))
    gezogene = {
        "zahlen": sorted(random.sample(seltene_zahlen[:30], 5)),
        "world": sorted(random.sample(seltene_world[:5], 2))
    }
    return gezogene

@app.route("/", methods=["GET", "POST"])
def index():
    global sim_jackpot, real_jackpot, freigabe_klasse1, fake_gewinner, ziehung, letzte_ziehung, gewinner_klassen, zeige_sim_jackpot

    if "email" not in session:
        return redirect(url_for("login"))
    email = session["email"]
    is_admin = session.get("admin", False)
    user_scheine = [s for s in scheine if s["email"] == email]
    message = ""

    if request.method == "POST":
        if is_admin:
            if "freigeben" in request.form:
                freigabe_klasse1 = not freigabe_klasse1
            elif "ziehen" in request.form:
                ziehung = ziehung_durchfuehren()
                letzte_ziehung = datetime.utcnow()
                limits = get_gewinnerlimits(sim_jackpot)
                gewinner_klassen.clear()
                klasse1_gewinner = []
                for s in scheine:
                    r = len(set(s["zahlen"]) & set(ziehung["zahlen"]))
                    w = len(set(s["world"]) & set(ziehung["world"]))
                    k = klassifizieren(r, w)
                    if not k: continue
                    if k == 1 and not freigabe_klasse1: continue
                    if k == 1:
                        klasse1_gewinner.append(s)
                        if len(klasse1_gewinner) > 3: continue
                    if k in limits:
                        gewinner_klassen.setdefault(k, []).append(s)
                        if len(gewinner_klassen[k]) > limits[k]:
                            gewinner_klassen[k] = gewinner_klassen[k][:limits[k]]
                    else:
                        gewinner_klassen.setdefault(k, []).append(s)
            elif "fake" in request.form:
                fake_email = request.form.get("fake_email")
                fake_gewinner.append(fake_email)
            elif "sim_betrag" in request.form:
                try:
                    sim_jackpot = int(request.form.get("sim_betrag"))
                except:
                    pass
            elif "real_betrag" in request.form:
                try:
                    real_jackpot = int(request.form.get("real_betrag"))
                except:
                    pass
            elif "toggle_sim" in request.form:
                zeige_sim_jackpot = not zeige_sim_jackpot
        else:
            zahlen = list(map(int, request.form.getlist("zahlen")))
            world = list(map(int, request.form.getlist("worldzahlen")))
            if len(zahlen) != 5 or len(world) != 2 or not all(1 <= z <= 50 for z in zahlen) or not all(1 <= w <= 10 for w in world):
                message = "Ungültige Zahlen!"
            elif len(user_scheine) >= max_scheine:
                message = "Max. 10 Spielscheine erlaubt."
            else:
                scheine.append({"email": email, "zahlen": sorted(zahlen), "world": sorted(world)})
                return redirect(url_for("index"))

    countdown = None
    if letzte_ziehung:
        naechste = letzte_ziehung + timedelta(days=7)
        diff = naechste - datetime.utcnow()
        if diff.total_seconds() < 0:
            diff = timedelta(days=7)
        tage = diff.days
        stunden, rest = divmod(diff.seconds, 3600)
        minuten, sekunden = divmod(rest, 60)
        countdown = f"{tage}d {stunden:02d}h:{minuten:02d}m:{sekunden:02d}s"

    gewinne = []
    if ziehung:
        for s in user_scheine:
            r = len(set(s["zahlen"]) & set(ziehung["zahlen"]))
            w = len(set(s["world"]) & set(ziehung["world"]))
            k = klassifizieren(r, w)
            if k:
                gewinne.append((s, k))

    return render_template("index.html",
        email=email,
        is_admin=is_admin,
        sim_jackpot=sim_jackpot,
        real_jackpot=real_jackpot if is_admin else None,
        zeige_sim_jackpot=zeige_sim_jackpot,
        user_scheine=user_scheine,
        freigabe=freigabe_klasse1,
        message=message,
        fake_gewinner=fake_gewinner,
        ziehung=ziehung,
        gewinne=gewinne,
        countdown=countdown
    )

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        if email == admin_email or email in testnutzer:
            session["email"] = email
            session["admin"] = (email == admin_email)
            return redirect(url_for("index"))
        else:
            return "Zugang verweigert"
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
