 Data Structures and Reasons for Their Use
 
This document lists every data structure used in the system, where
it appears, why it was chosen, and its complexity. Only structures
that serve a real purpose are listed.

---

## 1. Queue (FIFO) — `collections.deque`

**Used in:** `app/services/allocation_service.py`

**Where exactly:** Bay allocation — the pool of ordinary available
bays is stored in a `deque` and bays are handed out left-to-right.

**Why this structure?**

- Parking bays are a **shared, ordered resource**. FIFO ensures the
  bay that has been free longest is reused first — fair rotation,
  no starvation.
- `deque.popleft()` is **O(1)**, versus O(n) if we used a Python
  `list.pop(0)`.
- Bays are only pushed into the queue when they are `AVAILABLE`, so
  an occupied bay can never be dispatched.

**Complexity**

- Enqueue (bay released): O(1)
- Dequeue (bay allocated): O(1)
- Space: O(n), n = number of available bays

**Alternative considered:** A simple `list`. Rejected because
`pop(0)` is O(n) and would slow down allocation as the lot grows.

---

## 2. Hash Table (Python `dict`) — Active Sessions

**Used in:** `app/services/parking_service.py` →
`ParkingService._active_sessions_cache`

**Where exactly:** A dict mapping the normalised number plate
(e.g. `KDA123A`) to the id of the currently active `ParkingSession`.

**Why this structure?**

- The exit gate needs to answer *"Is this plate currently parked?"*
  in **O(1)**.
- A linear scan of all parking sessions would be O(n) and would get
  slower as the system ages.
- The dict is kept in sync on every entry and exit; if the process
  restarts, it is rebuilt lazily from the DB on the first miss.
- The DB remains the source of truth; the dict is only a cache.

**Complexity**

- Average lookup: O(1)
- Worst case: O(n) (collisions — vanishingly rare for plate strings)
- Space: O(m), m = active sessions

**Alternative considered:** A sorted list with binary search. O(log n),
but we would need to keep it sorted on every insert; the dict is
simpler and faster.

---

## 3. Priority Queue (min-heap) — Priority Bays

**Used in:** `app/services/allocation_service.py` → `priority_heap`

**Where exactly:** VIP / accessible / operational bays are pushed into
a `heapq` min-heap and are popped before ordinary bays.

**Why this structure?**

- Priority bays form a small, well-defined subset (~2 of 20).
- We want to serve the lowest-numbered available priority bay first,
  deterministically — a heap gives exactly that.
- Only the caller's need for "highest priority first" matters; the
  heap gives O(log n) push/pop which is more than fast enough.

**Complexity**

- Push: O(log n)
- Pop: O(log n)
- Space: O(k), k = number of available priority bays

**Alternative considered:** A plain list sorted after each insert.
O(n log n) rebuild — worse.

---

## 4. List — General Ordered Data

**Used in:** `app/models/*`, `app/services/report_service.py`,
`app/routes/*`

**Where exactly:** The results of most queries are Python lists:
- Bays rendered in the parking map
- Tariff rules returned in order
- Payment rows in reports
- Audit log entries

**Why this structure?**

- Lists preserve order and are the natural output of ORM queries.
- Iteration is O(1) per element; length is O(1).
- Fine for the sizes involved (tens to thousands of rows).

**Complexity:** Access O(1), scan O(n).

---

## 5. Stack (LIFO) — Audit Log "Recent Activity"

**Used in:** `app/routes/reports.py` → `audit_logs()`

**Where exactly:** The audit log is read newest-first
(`ORDER BY created_at DESC LIMIT 500`). Thematically this is a stack:
the most recent action is at the top.

**Why this concept?**

- A parking system is often debugged by looking at the latest events:
  "what happened in the last five minutes?"
- The newest-first view is exactly LIFO order without needing a
  physical stack — SQL can do it efficiently with an index on
  `created_at`.

**Complexity:** Same as a page through a list — O(k) where k = rows
fetched.

**Note:** We deliberately do not maintain a separate Python stack,
because the DB table is authoritative and indexed — a Python stack
would duplicate that without benefit.

---

## 6. Relational Tables — Persistent Data

**Used in:** All models in `app/models/`.

**Where exactly:** `users`, `roles`, `vehicles`, `parking_bays`,
`parking_sessions`, `tariffs`, `payments`, `audit_logs`,
`system_settings`.

**Why this structure?**

- The domain is fundamentally **relational**: one vehicle has many
  sessions, one session has many payments, one bay serves many
  sessions over time.
- ACID transactions prevent revenue loss (payment confirmed but
  bay still marked occupied).
- SQL provides free grouping, filtering, and indexing.

**Complexity:** Read by primary key O(1) with an index;
range scans O(log n + k) with a B-tree index.

---

## Summary Table

| Structure        | Purpose                    | Operation | Complexity |
|------------------|----------------------------|-----------|------------|
| Queue (deque)    | Bay allocation (FIFO)      | alloc     | O(1)       |
| Hash table (dict)| Active session lookup      | find      | O(1) avg   |
| Min-heap         | Priority bay selection     | pop       | O(log n)   |
| List             | Ordered query results      | scan      | O(n)       |
| Stack view       | Audit log (newest first)   | top-k     | O(k)       |
| Relational table | Persistence                | read      | O(1)/O(log n) |

