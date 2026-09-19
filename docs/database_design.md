Dynamic Database Design

**System:** Modern Parking Management System (web-based)
**Engine:** SQLite (dev), with MySQL/PostgreSQL compatibility via
`DATABASE_URL`. Managed through SQLAlchemy ORM.

The database is **dynamic** in three senses:

1. It is created and updated at runtime by the application itself
   (`db.create_all()` on first run, and ORM inserts/updates thereafter).
2. Business rules — parking tariffs, VAT rate, site name — live in
   the DB, not in source code, so management can change them without
   redeploying.
3. Foreign keys and cascades maintain integrity automatically.

---

## 1. Entity List

| Table              | Purpose                                            |
|--------------------|----------------------------------------------------|
| `roles`            | Role names: admin, attendant, auditor              |
| `users`            | Staff accounts (hashed password + role FK)         |
| `vehicles`         | One row per number plate ever seen                 |
| `parking_bays`     | Physical bays with current status                  |
| `parking_sessions` | One row per visit (entry → exit)                   |
| `tariffs`          | Fee bands stored in the DB, not in code            |
| `payments`         | One row per payment attempt (any method)           |
| `audit_logs`       | Append-only trail of important actions             |
| `system_settings`  | Key/value runtime configuration (VAT rate, etc.)   |

---

## 2. Relationships

| From              | Cardinality | To                | Meaning                              |
|-------------------|-------------|-------------------|--------------------------------------|
| `roles`           | 1 → many    | `users`           | One role is held by many users       |
| `users`           | 1 → many    | `parking_sessions`| Staff created / closed sessions      |
| `vehicles`        | 1 → many    | `parking_sessions`| One vehicle can park many times      |
| `parking_bays`    | 1 → many    | `parking_sessions`| One bay serves many sessions over time|
| `parking_sessions`| 1 → many    | `payments`        | One session can have several attempts|
| `users`           | 1 → many    | `audit_logs`      | One user performs many actions       |

All foreign keys are declared with `db.ForeignKey(...)`. Cascading
delete is used on `parking_sessions → payments` so that if a session
is removed (rare, admin-only), its payments go with it.

---

## 3. Primary Keys

Every table uses a synthetic `id INTEGER PRIMARY KEY AUTOINCREMENT`
(or its SQLAlchemy equivalent), which:

- Guarantees uniqueness without relying on business data.
- Keeps foreign keys small and fast to compare.
- Survives renames of business fields (e.g. if a plate is re-issued).

Business uniqueness is enforced separately with `UNIQUE` constraints
(see indexes below).

---

## 4. Foreign Keys

| Column                             | References        | On delete    |
|------------------------------------|-------------------|--------------|
| `users.role_id`                    | `roles.id`        | RESTRICT     |
| `parking_sessions.vehicle_id`      | `vehicles.id`     | RESTRICT     |
| `parking_sessions.bay_id`          | `parking_bays.id` | RESTRICT     |
| `parking_sessions.created_by`      | `users.id`        | SET NULL     |
| `parking_sessions.closed_by`       | `users.id`        | SET NULL     |
| `payments.parking_session_id`      | `parking_sessions.id` | CASCADE  |
| `audit_logs.user_id`               | `users.id`        | SET NULL     |

`RESTRICT` on bays and vehicles prevents accidental deletion of a bay
that is currently in use. `SET NULL` on user references preserves
historical records when staff leave.

---

## 5. Indexes

| Table              | Column(s)                                    | Reason                          |
|--------------------|----------------------------------------------|---------------------------------|
| `users`            | `username` (UNIQUE)                          | Login lookup                    |
| `vehicles`         | `number_plate` (UNIQUE)                      | Entry / exit plate lookup       |
| `parking_bays`     | `bay_number` (UNIQUE)                        | Map rendering, admin edits      |
| `parking_bays`     | `status`                                     | Availability queries            |
| `parking_sessions` | `ticket_number` (UNIQUE)                     | Ticket lookup                   |
| `parking_sessions` | `status`                                     | Active-session queries          |
| `parking_sessions` | `entry_time`, `exit_time`                    | Reports by date range           |
| `payments`         | `transaction_reference` (UNIQUE)             | Receipt / audit lookup          |
| `payments`         | `status`                                     | Revenue & failure reports       |
| `payments`         | `checkout_request_id`                        | M-Pesa callback matching        |
| `audit_logs`       | `action`, `created_at`                       | Audit views                     |

---

## 6. Normalisation

The schema is in **third normal form (3NF)**:

- **1NF:** Every column stores a single, atomic value. No repeating
  groups; each row is uniquely identified by `id`.
- **2NF:** No partial dependencies. Every non-key column depends on
  the *whole* primary key (which is a single surrogate `id`, so this
  is satisfied trivially).
- **3NF:** No transitive dependencies. For example, `payments` does
  not store the vehicle plate or the tariff amount — it stores a
  `parking_session_id`, and the session stores the bay and vehicle;
  the vehicle stores the plate. The tariff band used is derived at
  payment time and stored on `payments.amount` and
  `payments.net_amount`/`vat_amount`, so historical amounts are
  preserved even when tariffs change.

---

## 7. Dynamic Behaviours

### 7.1 Runtime-configurable tariffs

Tariffs live in the `tariffs` table. The fee engine
(`app/services/fee_service.py`) reads them from the DB **on every
calculation**. Management can add, edit, or deactivate a band via
`/tariffs/` in the UI. No source code changes are required.

**Effect on future sessions:** If management changes the fee for
"Up to 4 hours" from KES 100 to KES 120 at noon, then:

- All vehicles that exit *after* noon will be charged KES 120 for
  the 2–4-hour band.
- Vehicles that already exited have their historical amount stored
  in `payments.amount` and `parking_sessions.amount_due`, so
  reporting remains correct.

### 7.2 Runtime-configurable VAT

The VAT rate is stored in `system_settings` under key `vat_rate`.
`PaymentService._split_vat` reads it at the moment of confirmation
and stores both `net_amount` and `vat_amount` on the payment, so
changing the rate later does not retroactively alter old receipts.

### 7.3 Runtime-configurable bays

Administrators can add, deactivate, or mark bays out of service at
runtime. The allocation queue re-derives itself from the DB on every
allocation, so new bays are immediately available for allocation.

---

## 8. Referential Integrity & Transactions

The two most safety-critical operations are **entry** (allocate bay +
create session) and **exit** (confirm payment + close session +
release bay). Both are wrapped in a single SQLAlchemy transaction:
BEGIN
allocate bay
mark bay OCCUPIED
create session
COMMIT


If any step fails, `db.session.rollback()` runs and the DB stays
consistent. This prevents two failure modes:

- Bay marked OCCUPIED but no session → revenue would be lost.
- Session created but bay not marked OCCUPIED → a second car could be
  assigned to the same bay.

---

## 9. Concurrency

The system is designed so that two attendants cannot allocate the
same bay simultaneously:

- The allocation algorithm filters on `status = AVAILABLE`, so only
  bays that are currently free are considered.
- The chosen bay is immediately marked `OCCUPIED` inside the
  transaction, so a second concurrent allocation will not see it.
- On SQLite (single writer) the whole transaction is serialised by
  the file lock.
- On MySQL/PostgreSQL the same code path works because the UPDATE
  is atomic; a stricter implementation could add
  `SELECT ... FOR UPDATE` on the bay row for very high concurrency.