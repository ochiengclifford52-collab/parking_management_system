**Student:** [OGOLLA CLIFFORD]

**Reg No:** _[CIT-223-086/2025]_

**Unit:** Data Structures and Algorithms
**System:** Modern Parking Management System (web-based)

This document presents an algorithm for each module of the parking
system. Each algorithm lists its purpose, inputs, outputs, steps,
pseudocode, time complexity, and space complexity. The algorithms
here map directly to the code in `app/services/`.

---

## Module 1: User Authentication

**Purpose:** Verify a staff member's identity before allowing access.

**Input:** `username` (string), `password` (string)
**Output:** Authenticated user session or an error message

**Algorithm**

1. Look up the user by username.
2. If no user exists, return "invalid credentials".
3. Verify the submitted password against the stored hash
   (`werkzeug.security.check_password_hash`).
4. If the hash does not match, return "invalid credentials".
5. If the account is deactivated (`is_active = False`), refuse login.
6. Otherwise, create a session and record a `USER_LOGIN` audit event.

**Pseudocode**
function login(username, password):
user ← users.find(username)
if user is null:
return ERROR("invalid credentials")
if not check_password_hash(user.password_hash, password):
return ERROR("invalid credentials")
if not user.is_active:
return ERROR("account disabled")
create_session(user)
audit_log("USER_LOGIN", user.id)
return SUCCESS(user)


**Complexity**
- Time: O(1) average (hash lookup on the indexed `username` column)
- Space: O(1)

**Source:** `app/routes/auth.py`, `app/models/user.py`

---

## Module 2: Vehicle Registration (Entry)

**Purpose:** Record an arriving vehicle, allocate a bay, and open a
parking session.

**Input:** `number_plate` (string), `vehicle_type`, attendant id
**Output:** Parking session with assigned bay and ticket number

**Algorithm**

1. Normalise the plate (uppercase, remove spaces).
2. Validate the plate format against the Kenya plate regex.
3. Check the active-sessions hash table for a duplicate.
4. If duplicate, refuse.
5. Get or create the `Vehicle` record.
6. Dequeue the next available bay from the allocation queue.
7. If no bay exists, return `NO_AVAILABLE_SPACE`.
8. Mark the bay `OCCUPIED`.
9. Create the `ParkingSession` with a generated ticket number.
10. Commit the transaction.
11. Insert the plate→session id pair into the hash table.
12. Log `VEHICLE_ENTRY` and `BAY_ALLOCATED`.

**Pseudocode**
function register_entry(plate, user_id):
plate ← normalise(plate)
if not valid_plate(plate):
return ERROR("INVALID_PLATE")
if active_sessions.contains(plate):
return ERROR("DUPLICATE_ACTIVE")

BEGIN TRANSACTION
vehicle ← vehicles.find_or_create(plate)
bay ← allocate_bay() // FIFO queue dequeue
if bay is null:
ROLLBACK
return ERROR("NO_AVAILABLE_SPACE")
bay.status ← OCCUPIED
session ← create_session(vehicle, bay, now(), ticket=generate_ticket())
COMMIT

active_sessions[plate] ← session.id // hash table insert
audit_log("VEHICLE_ENTRY", session.id)
return SUCCESS(session, bay)

**Complexity**
- Time: O(1) average (hash lookup + queue dequeue)
- Space: O(1) additional

**Source:** `app/services/parking_service.py`

---

## Module 3: Parking Bay Allocation

**Purpose:** Assign the next free bay fairly.

**Input:** None (queries the DB)
**Output:** A `ParkingBay` object or `None`

**Algorithm**

1. Query bays where `status = AVAILABLE`, ordered by `bay_number`.
2. Split into two structures:
   - A **min-heap** of priority bays (VIP/accessible)
   - A **FIFO deque** of ordinary bays
3. If the heap has any element, pop it → return.
4. Else if the deque is non-empty, popleft → return.
5. Else return `None`.

**Pseudocode**
function allocate_bay():
priority_heap ← min_heap()
normal_queue ← deque()
for each bay in available_bays:
if bay.is_priority:
heappush(priority_heap, (bay.bay_number, bay.id))
else:
normal_queue.append(bay.id)
if not priority_heap.empty():
return heappop(priority_heap).bay
if not normal_queue.empty():
return popleft(normal_queue).bay
return None


**Complexity**
- Time: O(n) to build the structures; O(log n) for the heap pop; O(1) for the deque pop
- Space: O(n) where n = number of available bays

**Why a Queue?** FIFO guarantees fair rotation. Since only
`AVAILABLE` bays enter the structures, an occupied bay can never be
handed out. The heap ensures priority bays are considered first.

**Source:** `app/services/allocation_service.py`

---

## Module 4: Parking Search (Active Session Lookup)

**Purpose:** Find the active session of a plate at the exit gate.

**Input:** `number_plate` (string)
**Output:** `ParkingSession` or `None`

**Algorithm**

1. Normalise the plate.
2. Look up the plate in the in-memory hash table `_active_sessions_cache`.
3. If found and still active, return.
4. Otherwise, query the DB, repopulate the cache, and return.

**Pseudocode**
function get_active_session(plate):
key ← normalise(plate)
if active_sessions has key:
s ← load(active_sessions[key])
if s.is_active:
return s
active_sessions.remove(key)
vehicle ← vehicles.find(key)
if vehicle is null:
return None
s ← sessions.find_active(vehicle.id)
if s is not null:
active_sessions[key] ← s.id
return s


**Complexity**
- Average: O(1)
- Worst case: O(n) (rare hash collision or cache miss)

**Source:** `app/services/parking_service.py`

---

## Module 5: Fee Calculation

**Purpose:** Convert entry/exit timestamps into a KES amount using
DB-configured tariff bands.

**Input:** `entry_time`, `exit_time`, active tariffs
**Output:** Fee breakdown (duration + applicable band + amount)

**Algorithm**

1. Compute `delta = exit_time − entry_time`.
2. Convert seconds to minutes using `ceil` (partial minutes round up).
3. Load active tariff rules; sort by `max_duration_minutes` ascending.
4. Walk the sorted list; the first rule whose upper edge ≥ duration wins.
5. If duration exceeds every rule, use the last (largest) rule.
6. Return the amount.

**Pseudocode**
function calculate_fee(entry, exit, tariffs):
seconds ← max(0, (exit - entry).total_seconds())
minutes ← ceil(seconds / 60)
tariffs ← sort(tariffs by max_duration_minutes asc)
for rule in tariffs:
if minutes <= rule.max_duration_minutes:
return { amount: rule.amount, band: rule.name }
return { amount: last(tariffs).amount, band: last(tariffs).name }


**Boundary behaviour**

| Duration          | Band        | Fee (KES) |
|-------------------|-------------|-----------|
| 5 min             | ≤30 min     | 0         |
| exactly 30 min    | ≤30 min     | 0         |
| 30 min 1 s (→31)  | ≤2 h        | 50        |
| exactly 2 h       | ≤2 h        | 50        |
| 2 h 1 min         | ≤4 h        | 100       |
| exactly 4 h       | ≤4 h        | 100       |
| exactly 6 h       | ≤6 h        | 300       |
| 6 h 1 min         | over 6 h    | 500       |

**Complexity**
- Time: O(k log k) where k = number of tariff rules (small, ≤ 6)
- Space: O(k)

**Source:** `app/services/fee_service.py`

---

## Module 6: Payment Processing (State Machine)

**Purpose:** Enforce a correct lifecycle for every payment attempt.

**Input:** session, amount, payment method
**Output:** A `Payment` row whose status changes through a defined
state machine.

**State machine**
PENDING ──confirm──► CONFIRMED ──refund──► REFUNDED
│
├──fail───────► FAILED
└──cancel─────► CANCELLED


**Rules**

- A payment can leave `PENDING` only once.
- A payment cannot go from `FAILED` to `CONFIRMED` — a new attempt
  must be created instead.
- Only a `CONFIRMED` payment authorises the barrier to open.

**Pseudocode**
function confirm(payment_id, ext_ref):
p ← payments.find(payment_id)
if p.status == CONFIRMED:
return SUCCESS(p, already=True) // idempotent
if p.status != PENDING:
return ERROR("invalid transition")
p.status ← CONFIRMED
p.confirmed_at ← now()
p.external_ref ← ext_ref
session.status ← PAID
COMMIT
audit_log("PAYMENT_CONFIRMED", p.id)
return SUCCESS(p)


**Complexity**
- Time: O(1)
- Space: O(1)

**Source:** `app/services/payment_service.py`

---

## Module 7: M-Pesa Payment (STK Push)

**Purpose:** Send an STK Push prompt to the customer's phone and
confirm the payment via a Safaricom callback.

**Input:** payment, phone number
**Output:** A `PENDING` payment; a later callback moves it to
`CONFIRMED` or `FAILED`.

**Algorithm**

1. Normalise the phone number to `2547XXXXXXXX`.
2. Fetch an OAuth bearer token from Daraja.
3. Build the STK payload (amount, callback URL, timestamp, password).
4. POST to `/mpesa/stkpush/v1/processrequest`.
5. Store `MerchantRequestID` and `CheckoutRequestID`.
6. Return "accepted".
7. When the callback arrives, look up the payment by `CheckoutRequestID`.
8. **Duplicate-callback protection:** if the payment is no longer
   `PENDING`, ignore the callback.
9. If `ResultCode == 0`, confirm; else fail.

**Pseudocode**
function initiate_stk(payment, phone):
phone ← normalise(phone)
token ← get_oauth_token()
response ← POST /stkpush (amount, phone, callback, password)
if response.ResponseCode == "0":
payment.checkout_id ← response.CheckoutRequestID
COMMIT
return SUCCESS
else:
return ERROR(response)

function handle_callback(payload):
stk ← payload.Body.stkCallback
payment ← payments.find_by_checkout(stk.CheckoutRequestID)
if payment is null:
return ERROR("unknown checkout id")
if payment.status != PENDING:
return SUCCESS(duplicate=True) // idempotent
if stk.ResultCode == 0:
receipt ← extract MpesaReceiptNumber
return confirm(payment.id, receipt)
else:
return fail(payment.id, stk.ResultDesc)


**Complexity**
- Time: O(1) plus network latency
- Space: O(1)

**Source:** `app/services/mpesa_service.py`

---

## Module 8: Exit Processing

**Purpose:** Close a session after payment and release the bay.

**Input:** `session_id`, attendant id
**Output:** The finalised session + confirmed payment

**Algorithm**

1. Load the session.
2. If already `EXITED`, refuse.
3. Require a `CONFIRMED` payment for this session.
4. Record `exit_time`, `duration_minutes`, `amount_due`.
5. Set session to `EXITED`.
6. Release the bay (mark `AVAILABLE`).
7. Remove the plate from the active-sessions hash table.
8. Log `VEHICLE_EXIT` and `BAY_RELEASED`.

**Pseudocode**
function finalise_exit(session_id, user_id):
s ← sessions.find(session_id)
if s is null: return ERROR("not found")
if s.status == EXITED: return ERROR("already exited")
confirmed ← payments.find(session_id, status=CONFIRMED)
if confirmed is null: return ERROR("PAYMENT_NOT_CONFIRMED")
s.exit_time ← now()
s.duration_minutes ← fee.duration.minutes
s.amount_due ← fee.amount
s.status ← EXITED
s.bay.status ← AVAILABLE
COMMIT
active_sessions.remove(s.vehicle.number_plate)
audit_log("VEHICLE_EXIT", s.id)
return SUCCESS(s, confirmed)


**Complexity**
- Time: O(1)
- Space: O(1)

**Source:** `app/services/parking_service.py`

---

## Module 9: Exit Barrier Control

**Purpose:** Physically (or in simulation, logically) open the barrier
only when a confirmed payment exists.

**Input:** `session_id`
**Output:** Barrier state, or a refusal reason

**Algorithm**

1. Load the session.
2. If no session, refuse.
3. Look up a `CONFIRMED` payment for that session.
4. If none, log `BARRIER_OPEN_REFUSED` and refuse.
5. Otherwise transition `CLOSED → OPENING → OPEN`.
6. Log `BARRIER_OPENED`.

**Pseudocode**
function open_barrier(session_id):
s ← sessions.find(session_id)
if s is null: return ERROR("not found")
if not payments.exists(session_id, CONFIRMED):
audit_log("BARRIER_OPEN_REFUSED")
return ERROR("PAYMENT_NOT_CONFIRMED")
state ← OPENING
state ← OPEN
audit_log("BARRIER_OPENED")
return SUCCESS


**Complexity**
- Time: O(1)
- Space: O(1)

**Source:** `app/services/barrier_service.py`

---

## Module 10: Revenue Aggregation

**Purpose:** Total payments per day / week / month for reporting.

**Input:** Date range, optional filters
**Output:** Sum of confirmed payments

**Algorithm**

1. Filter payments to `status = CONFIRMED` and `confirmed_at ∈ [start, end)`.
2. Sum the `amount` column.
3. For per-day reports, `GROUP BY date(confirmed_at)`.

**Pseudocode**
function revenue_between(start, end):
return SUM(payments.amount)
WHERE status = 'CONFIRMED'
AND confirmed_at >= start
AND confirmed_at < end


**Complexity**
- Time: O(n log n) with index-assisted grouping
- Space: O(1) per aggregate

**Source:** `app/services/report_service.py`

---

## Module 11: Report Generation

**Purpose:** Produce revenue, VAT, method breakdown, occupancy, and
audit reports.

**Input:** Report type, date range
**Output:** Aggregated rows for display and CSV export

**Algorithm**

1. Accept a report type and date range.
2. Build a SQL aggregate query appropriate to the type.
3. Return ordered rows.
4. For CSV, iterate rows and write with the `csv` module.

**Complexity** O(n log n) per report.

**Source:** `app/services/report_service.py`, `app/routes/reports.py`

