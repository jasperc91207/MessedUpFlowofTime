from flask import Flask, render_template, redirect, url_for, session
import json
import random
from pathlib import Path

app = Flask(__name__)
app.secret_key = "change-this-later"  # Change before deploying

DATA_PATH = Path("poems.json")
ALLOWED_MODES = {"random", "chronological", "reverse", "motif"}


def load_poems():
    """Load poem/archive entries from JSON."""
    with open(DATA_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def get_poem_by_id(poem_id):
    """Find one poem by its id."""
    poems = load_poems()
    for poem in poems:
        if poem["id"] == poem_id:
            return poem
    return None


def make_mode_order(mode):
    """
    Return a stable list of poem ids in the order determined by a mode.
    - random: shuffled, stored in session so Next is stable
    - chronological: oldest to newest
    - reverse: newest to oldest
    - motif: grouped by first motif tag
    """
    poems = load_poems()

    if mode == "chronological":
        ordered = sorted(poems, key=lambda p: p["date"])
    elif mode == "reverse":
        ordered = sorted(poems, key=lambda p: p["date"], reverse=True)
    elif mode == "motif":
        ordered = sorted(poems, key=lambda p: p["motifs"][0] if p.get("motifs") else "")
    else:
        ordered = poems[:]
        random.shuffle(ordered)

    return [p["id"] for p in ordered]


def get_current_order(mode):
    """
    Get the current poem order from the session.
    Regenerate if the mode changed or doesn't exist.
    """
    session_mode = session.get("mode")
    order = session.get("mode_order")

    if session_mode != mode or not order:
        order = make_mode_order(mode)
        session["mode"] = mode
        session["mode_order"] = order

    return order


def add_to_reading_history(poem_id):
    """Store read poems in the session. Preserve order, avoid duplicates."""
    history = session.get("history", [])
    if poem_id not in history:
        history.append(poem_id)
    session["history"] = history


def get_reading_history():
    """Return poem objects for the poems already read."""
    poems = load_poems()
    history_ids = session.get("history", [])
    poem_lookup = {p["id"]: p for p in poems}
    return [poem_lookup[pid] for pid in history_ids if pid in poem_lookup]


def get_next_poem_id(mode, current_poem_id):
    """Determine the next poem based on the selected mode."""
    ids = get_current_order(mode)
    if not ids:
        return None
    if current_poem_id not in ids:
        return ids[0]
    current_index = ids.index(current_poem_id)
    next_index = (current_index + 1) % len(ids)
    return ids[next_index]


@app.route("/")
def title():
    """Black cover/title screen."""
    return render_template("title.html")


@app.route("/menu")
def menu():
    """Mode selection menu."""
    modes = [
        {
            "id": "random",
            "name": "Random Timeline",
            "description": "Poems appear in a shuffled, distorted order."
        },
        {
            "id": "chronological",
            "name": "Chronological Timeline",
            "description": "Poems appear from earliest to latest."
        },
        {
            "id": "reverse",
            "name": "Reverse Timeline",
            "description": "Poems appear from latest to earliest."
        },
        {
            "id": "motif",
            "name": "Motif Mode",
            "description": "Poems are loosely grouped by recurring images and themes."
        }
    ]
    return render_template("menu.html", modes=modes)


@app.route("/mode/<mode>")
def enter_mode(mode):
    """Enter a mode and redirect to the first poem. Resets reading path."""
    if mode not in ALLOWED_MODES:
        return "Mode not found.", 404

    order = make_mode_order(mode)
    session["mode"] = mode
    session["mode_order"] = order
    session["history"] = []

    if not order:
        return "No poems found."

    return redirect(url_for("reader", mode=mode, poem_id=order[0]))


@app.route("/browse/<mode>")
def browse(mode):
    """Browse all poems while preserving the active mode."""
    if mode not in ALLOWED_MODES:
        mode = "chronological"
    poems = load_poems()
    poems = sorted(poems, key=lambda p: p["date"])
    return render_template("browse.html", poems=poems, mode=mode)


@app.route("/mode/<mode>/poem/<poem_id>")
def reader(mode, poem_id):
    """Main poem reading interface."""
    if mode not in ALLOWED_MODES:
        return "Mode not found.", 404

    poem = get_poem_by_id(poem_id)
    if poem is None:
        return "Poem not found.", 404

    get_current_order(mode)
    add_to_reading_history(poem_id)

    history = get_reading_history()
    next_poem_id = get_next_poem_id(mode, poem_id)

    return render_template(
        "reader.html",
        poem=poem,
        mode=mode,
        history=history,
        next_poem_id=next_poem_id
    )


@app.route("/about")
def about():
    """About the author/project page."""
    return render_template("about.html")


@app.route("/reset-history")
def reset_history():
    """Clear reader history and return to the menu."""
    session["history"] = []
    return redirect(url_for("menu"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(__import__("os").environ.get("PORT", 5000)))

