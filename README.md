# Recover AI

**Recover AI** is an AI-powered financial transaction recovery and decision system. It autonomously analyzes failed, abandoned, or overdue payments, retrieves compliance/recovery policies, makes a decision using an AI agent, passes the decision through safety guardrails, and executes recovery actions—all while maintaining a comprehensive audit trail.

---

##  Architecture & Judging Information
For ease of judging, this project has been pre-configured to run out-of-the-box on a fresh clone using **SQLite**.

There is no need to manually install or configure PostgreSQL. All dashboard metrics, recoveries, decisions, guardrails, and pipelines are powered by the local SQLite database which you can initialize instantly using the provided synthetic dataset.

### Key Features to Verify
- **Risk Assessment:** Analyzes transactions based on failure codes (e.g. `insufficient_funds`, `do_not_honor`) and amounts to calculate a risk score.
- **Policy Engine:** Retrieves relevant recovery rules from the AI vector knowledge base using semantic overlap.
- **Decision Agent:** Determines the optimal recovery path (e.g., `retry_payment`, `send_payment_recovery_link`, `manual_review`).
- **Action Execution:** Executes simulated recovery actions and updates transaction states and recovered revenue based on confidence thresholds.
- **Guardrails:** Prevents duplicate executions, enforces maximum retry limits, and blocks unauthorized actions.
- **Audit Trail:** Logs every step of the pipeline.
- **Batch Processing:** Processes hundreds of transactions idempotently in the background.

---

## How It Works

Recover AI uses a deterministic multi-agent pipeline designed for financial safety:
1. **Trigger**: An open recovery case is picked up.
2. **Analyze**: The `Risk Engine` evaluates the transaction's failure reason and calculates a risk score and failure category (transient vs hard failure).
3. **Retrieve**: The `Policy Retriever` searches the internal `knowledge_bases` for compliance rules matching the failure context.
4. **Decide**: The `Decision Engine` selects an action. Crucially, the retrieved policies act as a hard constraint (e.g., if a policy says "do not automatically retry", a retry decision is downgraded to manual review).
5. **Execute**: The `Action Executor` attempts to recover the revenue (simulated based on confidence thresholds for the demo) and logs the outcome to an immutable audit trail.

---

##  Setup & Execution (Windows)

Follow these steps exactly to run the full end-to-end demo.

### 1. Backend Setup & Database Initialization

Open a PowerShell terminal and run:

```powershell
# Navigate to the Backend directory
cd Backend

# Create and activate a Python virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install backend dependencies
pip install -r requirements.txt

# Initialize the SQLite database and load the 500-transaction demo dataset
python -m scripts.seed_data

# Start the FastAPI backend server
uvicorn app.main:app --host 127.0.0.1 --port 8001
```

*The backend will now be running on `http://127.0.0.1:8001`.*

### 2. Frontend Setup

Open a **new** PowerShell terminal and run:

```powershell
# Navigate to the Frontend directory
cd Frontend

# Install Node dependencies
npm install

# Start the Vite development server
npm run dev
```

*The frontend will now be running on `http://127.0.0.1:5173`.*

---

##  How to Test and Judge the Workflow

Open the frontend at `http://127.0.0.1:5173` and follow this judging path:

### A. Dashboard Overview
- View the initial state of the synthetic dataset.
- Notice the **Revenue at Risk**, open cases, and failure distribution.

### B. Single Transaction Recovery
1. Navigate to the **Transactions** page.
2. Click on a `Failed`, `Overdue`, or `Abandoned` transaction.
3. Observe the Drawer UI. You will see the **Risk Engine Assessment** and the **AI Agent Decision** (along with its reasoning and applied policies).
4. Navigate to the **Cases** page and click on the associated Case ID.
5. In the top right, click **Run AI Recovery Workflow**.
6. Observe the visual pipeline tracker update as the transaction passes through Guardrails and is either **Recovered**, **Escalated**, or **Blocked**.
7. Scroll down to view the **Complete Recovery Audit Trail** logging the exact execution.

### C. Idempotency Guardrail Check
1. Try clicking **Run AI Recovery Workflow** on the same case again.
2. The UI will show a Guardrail violation blocking duplicate execution, proving the system is safe and idempotent.

### D. Batch Recovery
1. Navigate to the **Cases** page.
2. Click the **Run Batch Recovery** button.
3. Leave the limit at 500 and click **Start Batch Processing**.
4. The system will autonomously evaluate and execute the pipeline for all remaining open cases.
5. Review the resulting dialog showing exactly how much revenue was recovered and how many cases were escalated.
6. Return to the **Dashboard** to see the final recovered revenue metrics globally updated.

---

## How to Evaluate Recover AI

The easiest way to evaluate Recover AI is by using the bundled realistic transaction dataset. We have integrated **Judge Tools** directly into the frontend so you can test everything without touching the terminal.

1. **Start the Database & Import Data:**
   Run the seed script. By default, it will detect the bundled `data/realistic_transactions.csv` dataset and seed the SQLite database automatically.
   ```bash
   cd Backend
   python scripts/seed_data.py
   ```
2. **Start the Backend:**
   ```bash
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
   ```
3. **Start the Frontend:**
   ```bash
   cd Frontend
   npm run dev
   ```
4. **Explore the Dashboard:**
   Navigate to `http://127.0.0.1:5173`. You will see the operational dashboard loaded with realistic data representing open payment failures, risk assessments, and recovery metrics.

5. **Run Batch Recovery via UI:**
   Locate the **Judge Tools (Demo Controls)** section on the Dashboard and click **Run Batch Recovery**. The system will autonomously evaluate and execute the pipeline (Risk Assessment -> Policy -> Guardrails -> Action -> Audit Trail) for 100 cases.

6. **Inspect the Results:**
   The dashboard metrics (including Revenue Recovered and the AI Activity Log) will refresh automatically. Open individual cases by clicking them in the AI Activity Log to inspect the exact reasoning, confidence score, and executed actions generated by the AI simulation.

### Testing Custom Data (CSV Import)
If you wish to test your own data, use the **Upload Custom CSV** button in the **Judge Tools** panel on the Dashboard. 
You can download the template CSV directly from the UI to ensure your data matches the schema.

**Required CSV Columns:**
- `transaction_id`: Unique identifier (string)
- `amount`: Numeric value (e.g., 150.00)
- `status`: One of `failed`, `successful`, `abandoned`, `overdue`
- `customer_email`: Email address
- `timestamp`: ISO-8601 string (e.g., 2026-09-01T10:00:00Z)

*Optional Columns:* `customer_name`, `currency`, `payment_method`, `failure_code`, `failure_reason`.

---

## Data Source & Dataset Notice
The demo uses `data/realistic_transactions.csv`. 

To maintain independence and comply with PII/redistribution rules, this dataset was mathematically generated to mirror the distribution parameters of real-world public financial transaction datasets (such as Kaggle PaySim and Stripe open data) rather than including verbatim stolen/fraud records. 

It contains realistic failure codes (e.g., `insufficient_funds`, `do_not_honor`, `card_declined`) and realistic timestamps to allow the risk engine to appropriately categorize transient vs. hard failures. It is completely safe to distribute and use for this demonstration.

---

##  API Endpoints
If you wish to test the API directly via Postman or curl, the backend runs on port `8001`:

- **Dashboard Metrics:** `GET /api/v1/recovery/dashboard`
- **List Transactions:** `GET /api/v1/recovery/transactions`
- **List Cases:** `GET /api/v1/recovery/cases`
- **Get Case Detail:** `GET /api/v1/recovery/cases/{id}`
- **Single Recovery:** `POST /api/v1/recovery/cases/{id}/execute`
- **Batch Recovery:** `POST /api/v1/recovery/run?limit=500`
- **CSV Import:** `POST /api/v1/recovery/import`

---
*Developed for submission.*
