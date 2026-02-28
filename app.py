from flask import Flask, render_template, request, redirect, session, url_for
import imaplib
import email
from email.header import decode_header

app = Flask(__name__)
app.secret_key = "supersecretkey"


# ==========================================
# SMART SCORE-BASED CLASSIFIER
# ==========================================
def classify_email(subject, body):
    text = (subject + " " + body).lower()

    categories = {
        "Spam": [
            "lottery", "winner", "prize", "urgent",
            "claim now", "free money", "verify your account",
            "click below", "limited offer", "earn money",
            "work from home", "discount", "jackpot", "subscription","free trail","free gift",
            "cashback","reward","investment opportunity","double your money",
            "buy now","shop now","exclusive deal","discount","sale end soon","clearance","best price",
            "promo code","coupon",
            "opportunity", "limited time", "hurry", "don't miss out"
        ],
        "Parent Query": [
           "parent", "parent of", "i am the parent", "my son", "my daughter",
            "my child", "my ward", "regarding my child",
            "parent teacher meeting", "ptm",
            "semester fee", "fee payment", "tuition fee",
            "late payment", "payment fine", "fee structure"
        ],
        "Administration": [
            "notice", "circular", "announcement", "update",
            "memo", "policy", "guidelines",
            "admin office", "principal", "hod",
            "official meeting", "timetable",
            "admission", "admit card", "exam schedule"
        ],
        "Student Query": [
            "student",
            "assignment", "exam", "marks", "grade",
            "attendance", "leave", "project",
            "internship", "recommendation",
            "submission", "deadline",
            "course", "syllabus", "curriculum"
        ],
        "Events": [
            "event", "function", "festival", "celebration",
            "competition", "sports day", "annual day",
            "workshop", "seminar", "conference",
            "webinar", "guest lecture", "alumni meet"
        ]
    }

    scores = {}
    for category, keywords in categories.items():
        scores[category] = sum(text.count(word) for word in keywords)

    best_category = max(scores, key=scores.get)

    if scores[best_category] == 0:
        return "Student Query"

    return best_category


# ==========================================
# FETCH EMAILS
# ==========================================
def fetch_and_classify(email_user, email_pass):
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(email_user, email_pass)
    mail.select("inbox")

    status, messages = mail.search(None, "ALL")
    email_ids = messages[0].split()

    result = {
        "Student Query": [],
        "Parent Query": [],
        "Administration": [],
        "Events": [],
        "Spam": []
    }

    for eid in email_ids[-20:]:
        _, msg_data = mail.fetch(eid, "(RFC822)")

        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])

                # Decode subject
                subject = msg.get("Subject", "(No Subject)")
                decoded = decode_header(subject)[0][0]
                if isinstance(decoded, bytes):
                    subject = decoded.decode(errors="ignore")
                else:
                    subject = str(decoded)

                # Get sender
                sender = msg.get("From", "Unknown Sender")
                
                # Get date
                date = msg.get("Date", "")

                # Decode body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            payload = part.get_payload(decode=True)
                            if payload:
                                body = payload.decode(errors="ignore")
                            break
                else:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        body = payload.decode(errors="ignore")

                category = classify_email(subject, body)

                result[category].append({
                    "subject": subject,
                    "sender": sender,
                    "date": date,
                    "body": body[:500]
                })

    mail.logout()
    return result


# ==========================================
# ROUTES
# ==========================================

@app.route("/")
def login():
    return render_template("login.html")


@app.route("/fetch", methods=["POST"])
def fetch():
    email_user = request.form["email"]
    email_pass = request.form["password"]

    try:
        result = fetch_and_classify(email_user, email_pass)
        session["emails"] = result
        session["logged_in"] = True
        return redirect(url_for("dashboard"))

    except Exception as e:
        return f"""
        <h2>Login Failed</h2>
        <p>Make sure:</p>
        <ul>
            <li>2-Step Verification is ON</li>
            <li>You are using Gmail App Password</li>
        </ul>
        <br>Error: {str(e)}
        """


@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in"):
        return redirect("/")

    emails = session.get("emails", {})
    ordered_categories = ["Student Query", "Parent Query", "Administration", "Events", "Spam"]

    counts = []
    for category in ordered_categories:
        counts.append({
            "name": category,
            "count": len(emails.get(category, []))
        })

    return render_template("dashboard.html", counts=counts)


@app.route("/category/<name>")
def category(name):
    if not session.get("logged_in"):
        return redirect("/")

    emails = session.get("emails", {}).get(name, [])
    return render_template("category.html", emails=emails, name=name)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)