# Modern Parking Management System (MPMS)

**Multimedia University of Kenya — Data Structures and Algorithms Assignment**

A web-based parking management system that automates vehicle entry, bay
allocation, fee calculation, multi-method payment (M-Pesa / card / cash),
barrier control, and revenue reporting for a Kenyan parking facility.

---

## Academic Deliverables — Task One

The written answers to the assignment's three sub-questions are in the
`docs/` folder:

- [Algorithms for each module](docs/task_one_algorithms.md)
- [Data structures and their justification](docs/task_one_data_structures.md)
- [Dynamic database design](docs/task_one_database_design.md)

---

## Problem Statement

Small and medium parking facilities in Kenya typically operate manually.
The consequences are:

- Revenue leakage — no reliable record of every shilling collected.
- Slow exits at the gate.
- Unfair or random bay allocation.
- No audit trail for reconciliation or VAT reporting.
- Fee disputes because rates are not transparent.

This system addresses all of these with a data-driven, auditable,
web-based solution.

---

## Objectives

1. Record every arriving vehicle and allocate a bay algorithmically.
2. Compute parking duration and fees from **database-driven** tariffs.
3. Display a live visual map of available and occupied bays.
4. Accept payment by M-Pesa, card, and cash.
5. Open the exit barrier **only after confirmed payment**.
6. Produce an append-only audit log of every important action.
7. Produce revenue, VAT, and bay-utilisation reports.
8. Demonstrate the practical use of data structures and algorithms.

---

## Features

- **Authentication and role-based access** — administrator, attendant, auditor
- **Live parking map** — green (available), red (occupied), grey (out of service)
- **FIFO + priority queue bay allocation** with a min-heap for priority bays
- **Hash-table lookup** of active sessions by number plate — O(1) average
- **DB-driven tariffs** — add, edit, activate, or deactivate bands at runtime
- **Fee engine** — no hard-coded KES values anywhere in the code
- **Three payment methods**
  - M-Pesa (real Safaricom Daraja sandbox integration)
  - Card (simulated for the assignment)
  - Cash (with change calculation)
- **DEMO payment mode** — a clearly labelled local simulator when Daraja
  credentials are unavailable
- **Payment state machine** — PENDING → CONFIRMED / FAILED / CANCELLED / REFUNDED
- **Barrier safety** — refuses to open unless a CONFIRMED payment exists
- **Receipt generation** — printable, with net / VAT / gross breakdown
- **Audit log** — append-only from the UI
- **Reports** — daily, weekly, monthly revenue; payment methods; VAT;
  bay utilisation; failed payments; CSV export
- **Automated tests** with pytest

---

## Technologies

| Layer          | Technology                                              |
|----------------|---------------------------------------------------------|
| Backend        | Python 3.10+, Flask 3, Flask-Login, Flask-WTF           |
| Database       | SQLite (dev), MySQL / PostgreSQL compatible             |
| ORM            | SQLAlchemy 2.x through Flask-SQLAlchemy                 |
| Frontend       | HTML5, CSS3, Bootstrap 5, vanilla JS, Chart.js          |
| Payments       | Safaricom Daraja (STK Push) + a local demo simulator    |
| Testing        | pytest                                                  |
| Version control| Git / GitHub                                            |

---

## System Architecture
Browser (HTML + Bootstrap + JS)
|
| HTTP
v
Flask blueprints -> services -> SQLAlchemy models -> SQLite / MySQL / PostgreSQL
|
+--> External services: Safaricom Daraja, Demo simulator,
Barrier simulator, Audit logger

text

Highlights:

- **Blueprints** keep routes separated by domain
  (`auth`, `dashboard`, `parking`, `payments`, `reports`, `tariffs`, `admin`, `public`).
- **Services** hold all business logic and are unit-testable independently.
- **Models** are SQLAlchemy ORM classes with proper indexes and foreign keys.

---

## Data Structures Used

| Structure         | Where                          | Purpose                          | Complexity   |
|-------------------|--------------------------------|----------------------------------|--------------|
| Queue (deque)     | Bay allocation                 | Fair FIFO rotation of free bays  | O(1)         |
| Hash table (dict) | Active session lookup          | Fast plate search at exit gate   | O(1) average |
| Min-heap          | Priority bays (VIP / accessible) | Serve priority bays first      | O(log k)     |
| List              | Query results                  | Ordered iteration for templates  | O(n) scan    |
| Stack (logical)   | Audit log view (newest first)  | Recent-activity debugging        | O(k)         |
| Relational tables | All persistence                | ACID, FKs, SQL aggregation       | varies       |

Full write-up: [docs/task_one_data_structures.md](docs/task_one_data_structures.md)

---

## Algorithms

See [docs/task_one_algorithms.md](docs/task_one_algorithms.md) for
full pseudocode and complexity for each module. Brief summary:

- **Bay allocation** — priority heap first, then FIFO deque.
- **Active-session lookup** — hash table with a database fallback.
- **Fee calculation** — sort tariffs ascending by `max_duration_minutes`
  and pick the first band whose upper edge is ≥ the session duration.
  No hard-coded KES values.
- **Payment state machine** — enforced transitions with idempotent
  confirmation.
- **Exit processing** — transactional; requires a confirmed payment;
  releases the bay atomically.

---

## Installation

Prerequisites:

- Python 3.10 or newer
- Git
- (Optional) A virtual-environment tool such as `venv`

Steps:

```bash
git clone https://github.com/<your-username>/parking_management_system.git
cd parking_management_system
python -m venv venv

# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env     # Windows: copy .env.example .env
Edit .env and set SECRET_KEY to a random string. For the local
demo, leave PAYMENT_MODE=demo.

Database Setup
The application creates its schema on first run. To populate it with
demo data (roles, users, 20 bays, tariff bands, settings):

bash
python scripts/seed_database.py
Expected output:

text
[OK] Database seeded successfully.
     Users:   3
     Bays:    20
     Tariffs: 5

     Login credentials:
       admin      / ChangeMe123!
       attendant  / ChangeMe123!
       auditor    / ChangeMe123!
     CHANGE THESE PASSWORDS after first login.
Running the Application
bash
python run.py
Then open:

URL	Purpose
http://127.0.0.1:5000/	Public driver availability
http://127.0.0.1:5000/login	Staff login
http://127.0.0.1:5000/dashboard	Staff dashboard
Default Credentials
Role	Username	Password
Administrator	admin	ChangeMe123!
Attendant	attendant	ChangeMe123!
Auditor	auditor	ChangeMe123!
Change these passwords immediately in any non-demo environment.
Use the Admin page (/admin/) to create new users or toggle existing
ones.

M-Pesa Configuration
The system supports two clearly-separated modes selected by
PAYMENT_MODE in .env.

1. DEMO mode (default — no credentials needed)
No network call is made to Safaricom.

On the payment status page you are shown two buttons:
Simulate Successful Payment and Simulate Failed Payment.

The workflow is identical to real M-Pesa at the system level (same
PENDING → CONFIRMED / FAILED state machine), so the demo is honest:
no simulated transaction is ever presented as a real Safaricom one.

2. SANDBOX mode (real Daraja sandbox integration)
Register at https://developer.safaricom.co.ke.

Create an app to obtain a Consumer Key, Consumer Secret, and
Passkey for the sandbox.

Expose your local server publicly (e.g. ngrok http 5000) and use
the HTTPS URL as the callback.

Fill in .env:

text
PAYMENT_MODE=sandbox
MPESA_CONSUMER_KEY=...
MPESA_CONSUMER_SECRET=...
MPESA_SHORTCODE=174379
MPESA_PASSKEY=...
MPESA_CALLBACK_URL=https://<your-ngrok>.ngrok-free.app/payments/mpesa/callback
Restart the app. Real STK Push prompts will be delivered to the
phone number entered on the payment page.

Demonstration Walkthrough

Log in as admin / ChangeMe123! at /login.

The dashboard shows 20 bays all available.

Register vehicle KDA 123A at /parking/entry. The system
allocates a free bay and generates a ticket.

The dashboard now shows one bay occupied.

Backdate the session to simulate a 3-hour stay:

bash
python - <<'PY'
from app import create_app
from app.extensions import db
from app.models.parking_session import ParkingSession
from datetime import datetime, timedelta
app = create_app()
with app.app_context():
    s = ParkingSession.query.order_by(ParkingSession.id.desc()).first()
    s.entry_time = datetime.utcnow() - timedelta(hours=3)
    db.session.commit()
    print("Backdated", s.ticket_number, "to", s.entry_time)
PY
Go to /parking/exit, enter KDA 123A. The invoice shows
Duration 3h 0m, Applicable tariff: Up to 4 hours,
Amount due: KES 100.00.

Click Proceed to Payment. Choose M-Pesa, enter a phone number
such as 254712345678.

On the status page (DEMO mode), click Simulate Successful
Payment. The payment becomes CONFIRMED.

Click Open Barrier. The barrier simulator logs the event.

Click Finalise Exit & Show Receipt. The receipt shows the KES
100 payment with the correct VAT split.

Return to the dashboard: the bay is AVAILABLE again.

Open /reports/ — the KES 100 revenue is visible with VAT.

Open /reports/audit-logs — you can trace every event:
USER_LOGIN, VEHICLE_ENTRY, BAY_ALLOCATED, PAYMENT_INITIATED,
MPESA_DEMO_INITIATED, PAYMENT_CONFIRMED, BARRIER_OPENED,
VEHICLE_EXIT, BAY_RELEASED.

API Endpoints
Method	Endpoint	Description
POST	/login	Staff login
GET	/logout	Staff logout
GET	/api/availability	Public bay availability (JSON)
GET	/parking/api/availability	Staff availability (JSON)
POST	/parking/entry	Register arrival (HTML form)
POST	/parking/exit	Preview exit invoice
POST	/payments/checkout/<session_id>	Initiate payment
GET	/payments/status/<payment_id>	Payment status
GET	/payments/receipt/<payment_id>	Printable receipt
POST	/payments/mpesa/callback	Safaricom callback (public)
POST	/payments/demo/confirm/<payment_id>	Demo-only force success
POST	/payments/demo/fail/<payment_id>	Demo-only force failure
POST	/payments/barrier/open/<session_id>	Attempt to open barrier
POST	/payments/finalise/<session_id>	Finalise exit and release bay
GET	/tariffs/api	Active tariffs (JSON)
POST	/tariffs/add, /tariffs/edit/<id>, /tariffs/toggle/<id>	Manage rates
GET	/reports/	Revenue, VAT, utilisation
GET	/reports/revenue.csv	CSV export
GET	/reports/audit-logs	Audit trail
Testing
bash
pytest -v
Coverage includes:

Fee boundary cases (30 min, 2h, 4h, 6h, over 6h, 30m1s)

Bay allocation (FIFO, priority, exhaustion)

Duplicate plate rejection

Cash payment (insufficient and correct change)

M-Pesa demo flow and duplicate callback protection

Barrier refusal without confirmed payment

Payment state-machine transition rules

Authentication and role-based authorisation

Security
Passwords stored as Werkzeug hashes (never plaintext).

CSRF protection on all state-changing forms except the M-Pesa
callback (Safaricom cannot send a CSRF token; instead the callback
validates CheckoutRequestID against the database and is idempotent).

Role-based authorisation on all administrative routes.

All SQL goes through SQLAlchemy's parameterised queries — no SQL
injection.

Secrets live in .env, which is gitignored. .env.example shows
the shape only.

Card data: only the last 4 digits are stored, for the receipt.
No PAN, CVV, or PIN is ever recorded.

M-Pesa: the browser can never declare payment success. Only the
Daraja callback (or, in demo mode, the clearly-labelled simulator)
moves a payment from PENDING to CONFIRMED.

Project Structure
text
parking_management_system/
├── app/
│   ├── __init__.py            # Flask app factory
│   ├── config.py              # Configuration classes
│   ├── extensions.py          # db, login_manager, csrf
│   ├── models/                # SQLAlchemy models
│   ├── routes/                # Blueprints (auth, parking, payments, ...)
│   ├── services/              # Business logic (fee, payment, mpesa, barrier, ...)
│   ├── templates/             # Jinja2 templates
│   └── static/                # CSS, JS
├── docs/
│   ├── task_one_algorithms.md
│   ├── task_one_data_structures.md
│   └── task_one_database_design.md
├── scripts/
│   └── seed_database.py
├── tests/
├── instance/                  # SQLite database (gitignored)
├── .env.example
├── .gitignore
├── requirements.txt
├── run.py
└── README.md
Complexity Summary
Operation	Complexity
Bay allocation (FIFO)	O(1)
Bay allocation (priority)	O(log k)
Active-session lookup	O(1) average (hash table)
Fee calculation	O(k log k), k ≤ 6 tariffs
Payment state transition	O(1)
Revenue aggregation	O(n log n) with index
Occupancy count	O(n) over bays
Limitations
Card payment is simulated; a production system would integrate
Stripe, Flutterwave, or a similar gateway.

The barrier is a software simulation; hardware integration would use
GPIO, Modbus, or MQTT.

Plate entry is manual. A production system would use ANPR cameras.

Timestamps are stored in naive UTC. A production system should use
timezone-aware timestamps and display them in Africa/Nairobi.

Future Improvements
Real ANPR / camera integration for automatic plate capture.

Monthly season tickets and subscriber accounts.

Reserved-booking API for peak hours.

SMS and email receipts.

WebSocket live-update for the parking map (in place of polling).

Docker image for one-command deployment.

Kubernetes-ready container with MySQL backend.
