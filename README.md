# 🚀 Application Tracker

An automated, enterprise-grade SaaS platform designed to sync, parse, track, and analyze job applications directly from a user's Gmail mailbox. Built with a decoupled high-concurrency micro-architecture combining a Python FastAPI backend, a Celery/Redis asynchronous task queue, a PostgreSQL database, and a Next.js 14 frontend.

---

## 🏗️ Core System Architecture

The platform is designed around a decoupled, event-driven pattern. The backend handles lightweight HTTP requests synchronously and delegates heavy operations (mailbox syncing, email body downloads, and NLP-based entity extraction) to Celery background workers.

```
                           +------------------------+
                           |   Next.js 14 Client    |
                           +-----------+------------+
                                       | (REST / SSE)
                                       v
                           +------------------------+
                           |  FastAPI Backend API   | <---+ (OAuth Callback)
                           +-----+------------+-----+     |
                                 |            |           |
               (Read / Write)    |            | (Publish) |
          +----------------------+            +-------+   |
          |                                           |   |
          v                                           v   |
+---------+----------+                      +---------+---+--------+
| PostgreSQL DB      |                      | Redis 7 Broker       |
| (Asyncpg Engine)   |                      | & Pub/Sub Server     |
+--------------------+                      +---------+------------+
                                                      |
                                                      | (Poll / Dispatch)
                                                      v
                                            +---------+------------+
                                            | Celery Task Workers  |
                                            +---------+------------+
                                                      | (Fetch / Parse)
                                                      v
                                            +---------+------------+
                                            |   Gmail REST API     |
                                            +----------------------+
```

---

## 🛠️ Technology Stack & Dependencies

### Backend (Python 3.11+)
- **API Framework:** `FastAPI` (Asynchronous HTTP routing, Pydantic v2 data validation, and dependency injection).
- **ORM & Database Client:** `SQLAlchemy 2.0` (asyncio support) + `asyncpg` (PostgreSQL driver) + `psycopg` (sync driver for migrations).
- **Asynchronous Task Queue:** `Celery` + `Redis` (Broker and Result Backend).
- **Natural Language Processing (NLP):** `spaCy` (`en_core_web_sm` model) for Named Entity Recognition (NER).
- **Security & Cryptography:** `cryptography` (AES-256-GCM authenticated encryption) + `bcrypt` (work factor 12) + `python-jose` (JWT signatures).
- **Database Migrations:** `Alembic` (declarative schema migration management).
- **Rate Limiting:** `SlowAPI` (token-bucket rate limiting).
- **Structured Logging:** `structlog` (JSON structured logs for operational observability).
- **Test Suite:** `pytest` + `pytest-asyncio` + `factory-boy` (unit & integration testing).

### Frontend (Next.js 14+)
- **Framework:** `Next.js 14` (App Router, React Server Components, client-side route grouping).
- **State Management:** `Zustand` (minimalistic global client store for auth and workspace preferences).
- **Data Fetching & Caching:** `TanStack React Query v5` (optimistic UI updates, caching, automatic polling).
- **Form Validation:** `React Hook Form` + `Zod` (client-side validation schemas matching backend models).
- **CSS & UI Primitives:** `Tailwind CSS` + `Radix UI` (accessible headless primitives) + `lucide-react` (iconography).
- **Analytics Visualizations:** `Recharts` (composable responsive charts for metrics).
- **Toasts:** `Sonner` (asynchronous state toast notifications).

---

## ⚡ Technical Deep Dives

### 1. Mailbox Sync Engine & Rate Throttling
To process massive amounts of mailbox history without running into Gmail API quota limitations (rate-limiting errors/HTTP 429), the sync engine utilizes a custom paging and throttling pipeline:
* **Throttling with Semaphores:** During email metadata fetches, a semaphore is implemented (`MAX_CONCURRENT_REQUESTS = 10`) to limit parallel async HTTP tasks.
* **Sync Strategy:**
  * `INITIAL_IMPORT`: Initiated upon onboarding. Pulls all messages starting from the user's defined `initial_import_from` date.
  * `INCREMENTAL`: Pulls only emails received since the last verified `last_successful_sync_at` timestamp.
* **Database Optimization:** Emails are fetched in batches, parsed into metadata representations, and stored using bulk upserts (`bulk_upsert_emails` with PostgreSQL `INSERT ON CONFLICT DO UPDATE`) to prevent redundant records.
* **Server-Sent Events (SSE):** During synchronization, workers publish real-time progression events (`sync_started`, `page_processed`, `sync_completed`) to a Redis channel. The FastAPI backend streams these to the frontend using `sse-starlette` so users see live import progress.

### 2. Multi-Stage NLP Parsing Pipeline
Once new email headers are synced, they are passed to the parser service. To save CPU cycles and prevent fetching full bodies of irrelevant emails, a multi-stage approach is used:

```
[Sync Log Completed] -> [Pre-Filter Metadata Scan]
                              |
                     Is Job Related?
                              |
                    +---------+---------+
                    | No                | Yes
                    v                   v
             [Skip Email]        [Fetch Full Body from Gmail API]
                                        |
                                 [Classify Type] 
                                        |
                                 [Extract Status]
                                        |
                             [Extract Company & Role]
                             Domain mapping -> Regex -> spaCy NER
                                        |
                           [Deduplicate / Update DB]
```

1. **Pre-Filtering (Header-Level):** Evaluates the sender domain, subject line, and initial snippet using keyword-based heuristics. If the spam score outweigh the job score, the email is marked as parsed but ignored.
2. **Body Retrieval & Classification:** For emails that pass the pre-filter, the full text body is fetched from the Gmail API. An `EmailClassifier` determines the intent (e.g., Application Confirmation, Assessment Invite, Interview Invite, Offer, Rejection).
3. **Company & Role Extraction:**
   * **Domain Mapping (Highest Confidence):** Maps the sender's domain directly to a canonical company (e.g., `careers@google.com` -> `Google`).
   * **Deterministic Regex (Medium Confidence):** Parses email headers and body lines using strict regex patterns to extract common corporate naming conventions.
   * **spaCy NER Fallback (Low-to-Medium Confidence):** Employs the `en_core_web_sm` model to parse ORG and PERSON entities, applying custom string distance filters to strip legal suffixes (e.g., `LLC`, `Inc.`, `Ltd.`) and evaluate the most common organizational entities.

### 3. Deduplication Engine & Status Regression Guard
Since multiple emails are received during a single job application lifecycle (e.g., submission -> test -> interview -> offer), the service prevents duplicate tracking:
* **Thread-ID Deduplication:** Attempts to match the incoming email's `gmail_thread_id` to an active application. To enforce precision, it compares the company names using Python's `SequenceMatcher` with a similarity threshold of `0.85`.
* **Heuristic Clustering:** If no thread match exists, it scans the last 50 active applications for the user, checking for matching canonical company names and intersecting job roles.
* **Status Regression Guard:** Standardizes status ordering:
  `PENDING (0) -> APPLIED (1) -> ASSESSMENT (2) -> INTERVIEW (3) -> OFFER (4)`
  * Updates are ignored if the parsed status represents a regression (e.g., a delayed confirmation email stating "applied" will not overwrite a manually updated "interview" status).
  * `REJECTED` is treated as a terminal state.

### 4. Advanced Security & Data Cryptography
Data privacy is critical since the application accesses sensitive personal emails. The security layer implements several key cryptographical decisions:
* **Secure Token Hashing:** Password hashing uses `bcrypt` with a cost factor of `12` (the OWASP standard). Opaque, high-entropy (512-bit) refresh tokens are generated and stored in PostgreSQL using `SHA-256` hashing (since their length exceeds bcrypt's 72-byte limit). They are set on the client via `HttpOnly` cookies.
* **AES-256-GCM Token Encryption:** The Google API OAuth refresh tokens stored in the `gmail_connections` table represent a high-value target.
  * Tokens are encrypted prior to database insertion using **AES-256-GCM** (Galois/Counter Mode).
  * A fresh **96-bit random nonce** is generated for every encryption pass.
  * The resulting ciphertext contains the authenticated tag, protecting against ciphertext tampering (bit-flipping attacks).

### 5. Soft-Delete (Bin) Architecture
When users delete job tracking records, they are not immediately expunged:
* Deleted records have `is_deleted` set to `True`, which immediately filters them from dashboard calculations.
* A row is created in `DeletedApplication` which defines a retention threshold (`purge_after` date, default 30 days).
* A periodic Celery worker (`purge_expired_bin_records`) runs asynchronously to hard-delete expired rows, leveraging cascade constraints (`ON DELETE CASCADE`) to clean up status histories and email references.

### 6. Analytics Cache Layer
To keep Next.js dashboard charts loading instantly, application-wide analytics are decoupled from the query interface:
* A Celery task (`generate_analytics_task`) is dispatched asynchronously at the end of a sync-and-parse cycle.
* It aggregates metrics (active application counts, success rate, response rate, chronological trend charts).
* The aggregated JSON payload is saved directly in a JSONB field in the `application_analytics` table, meaning frontend dashboard fetches load in a single database read.

---

## 📁 Database Schema Details

The core schema includes the following tables:

| Table | Purpose | Key Attributes |
| :--- | :--- | :--- |
| `users` | Core user credentials and profile state | `id` (UUID), `email`, `hashed_password`, `is_active` |
| `user_sessions` | Audited active client sessions | `id`, `user_id`, `ip_address`, `user_agent`, `last_activity` |
| `gmail_connections` | OAuth integration tokens | `user_id` (PK), `encrypted_refresh_token` (AES), `initial_import_done` |
| `emails` | Synced headers and processed status of emails | `gmail_msg_id` (PK), `gmail_thread_id`, `sender`, `subject`, `is_parsed` |
| `applications` | The canonical tracked job positions | `id` (UUID), `company_name`, `role_title`, `current_status`, `is_deleted` |
| `application_status_history` | Audit log tracking chronological status changes | `id`, `application_id`, `status`, `detected_at`, `confidence_scores` |
| `deleted_applications` | Holds soft-deleted applications inside the Bin | `id`, `application_id`, `deleted_at`, `purge_after`, `is_purged` |
| `application_analytics` | Pre-calculated dashboard analytics cache | `user_id` (PK), `total_applications`, `interview_rate`, `monthly_data` (JSONB) |
| `sync_logs` | Audit tracking for background synchronization tasks | `id`, `user_id`, `sync_status`, `emails_synced`, `error_message` |

---

## 🚀 Setting Up the Application

### Prerequisites
- Docker & Docker Compose
- Node.js 18+ (if running frontend outside Docker)
- Python 3.11+ & Poetry (if running backend outside Docker)

### Setup Configurations

1. **Backend Environment (`backend/.env`):**
   Copy `backend/.env.example` to `backend/.env` and supply the required secrets:
   ```env
   # Database configuration
   DATABASE_URL=postgresql+asyncpg://jobtracker:password@db:5432/jobtracker_db
   
   # Security
   JWT_SECRET_KEY=generate_a_secure_random_hex_string_here_with_at_least_64_characters
   ENCRYPTION_KEY=base64_encoded_32_byte_aes_key
   
   # Redis / Celery
   REDIS_URL=redis://redis:6379/0
   
   # Gmail OAuth credentials
   GOOGLE_CLIENT_ID=your_google_client_id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your_google_client_secret
   ```

2. **Frontend Environment (`frontend/.env.local`):**
   Create a local configuration:
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

### Running the Application

The simplest way to run the entire system is using Docker Compose:

```bash
# Build and spin up the services (PostgreSQL, Redis, FastAPI, Celery, and Next.js)
docker-compose up --build
```

#### Manual Developer Setup (Non-Docker)

1. **Database Setup & Migrations:**
   ```bash
   cd backend
   poetry install
   # Run alembic migrations
   poetry run alembic upgrade head
   ```

2. **Run Backend API:**
   ```bash
   poetry run uvicorn app.main:app --reload --port 8000
   ```

3. **Run Celery Task Worker:**
   ```bash
   poetry run celery -A app.worker.celery_app worker --loglevel=info
   ```

4. **Run Frontend Development Server:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   Open `http://localhost:3000` to view the application dashboard.

---

## 🧪 Testing and Verification

A comprehensive test suite is included in the `backend` project using `pytest` to guarantee system stability and test-driven reliability.

```bash
cd backend
# Run unit and integration tests
poetry run pytest -v

# Run with test coverage reports
poetry run pytest --cov=app --cov-report=term-missing
```

The test coverage covers:
* Database session lifecycles and transactions.
* JWT authentication flows, session limits, and token refresh validation.
* Encryption verification (AES-256-GCM verification tests).
* Parsing logic including regex filters, keyword scoring models, and spaCy NER fallback tests.
* Application status priority logic and state machine progression updates.
