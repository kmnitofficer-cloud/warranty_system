# EquipGuard: Device Warranty Management & Notification System

EquipGuard is a modern, responsive, enterprise-grade Device Warranty Management and Notification System for office equipment and electronic devices. It couples a responsive HTML5/CSS3/JavaScript SaaS administrative dashboard with a Python Streamlit backend, integrating **Google Drive API** for cloud-synced Excel database storage, **Firebase Authentication** for secure access, and a multi-stage **Warranty Notification Engine**.

---

## 🚀 Key Highlights & Architecture

```
                                  ┌───────────────────────────────┐
                                  │      Web Browser (Client)     │
                                  │   HTML5 / CSS3 / JavaScript   │
                                  │  Chart.js / Responsive SaaS   │
                                  └──────────────┬────────────────┘
                                                 │ Bidirectional
                                                 │ Component Bridge
                                                 ▼
                                  ┌───────────────────────────────┐
                                  │     Streamlit Application     │
                                  │       (Python Backend)        │
                                  └──┬───────────┬──────────────┬─┘
                                     │           │              │
                   ┌─────────────────┘           │              └────────────────┐
                   ▼                             ▼                               ▼
       ┌───────────────────────┐   ┌───────────────────────────┐   ┌─────────────────────────┐
       │ Firebase Auth Service │   │ Dynamic Warranty Engine   │   │  OpenPyXL / Cloud Sync  │
       │   Email & Password    │   │ Milestones: 30,14,7,3,0 d │   │  4 Workbook Sheets:     │
       │  Sessions & Audit Log │   │ Strict De-duplication     │   │  Devices, Notifications,│
       └───────────────────────┘   └───────────────────────────┘   │  Activity_Log, Settings │
                                                                   └────────────┬────────────┘
                                                                                │ Google Drive API v3
                                                                                ▼
                                                                   ┌─────────────────────────┐
                                                                   │ Google Drive Primary DB │
                                                                   │ .xlsx Cloud Persistence │
                                                                   └─────────────────────────┘
```

- **Dual-Engine Architecture**: HTML5/CSS3/JavaScript administrative frontend rendered seamlessly inside Streamlit, communicating via postMessage with Python backend services.
- **Google Drive Excel Database**: Primary workbook (`Device_Warranty_Database.xlsx`) maintained in Google Drive with automatic folder/file creation, styled headers, and background synchronization.
- **Offline / Local Fallback**: Seamlessly runs with local Excel caching if Google Drive credentials have not yet been placed, allowing instant testing out of the box.
- **Firebase Authentication**: Email & Password authentication using the Firebase Identity Toolkit REST API with session state persistence and ready-to-test Demo credentials.
- **Milestone Notification Engine**: Alerts triggered at **30 days, 14 days, 7 days, 3 days**, and on **Expiration date (0 days)** with strict de-duplication to prevent duplicate alerts.
- **Desktop Browser Notifications**: HTML5 Web Notifications API support for instant OS-level desktop alerts.
- **Audit Analytics & Reports**: One-click export to styled **Excel (.xlsx)** and executive **PDF Audit Reports** generated via ReportLab.

---

## 🛠️ Technology Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Frontend** | HTML5, CSS3, Vanilla JS, Chart.js | Modern SaaS dark navy sidebar, responsive grid, dynamic charts, modals, toasts |
| **Backend** | Python Streamlit | Component orchestration, state management, API controllers |
| **Cloud Database** | Excel (`.xlsx`) via Google Drive API | 4 sheets: `Devices`, `Notifications`, `Activity_Log`, `Settings` |
| **Spreadsheet Engine** | OpenPyXL | High-performance formatted Excel manipulation with cell styling and thread locking |
| **Authentication** | Firebase Authentication | Email & Password authentication, JWT session verification |
| **PDF Generation** | ReportLab Platypus | Multi-page executive PDF audit reports with summary KPIs and inventory tables |
| **Alerts & Push** | In-app Badge + Web Notification API | Visual counter pills, dropdown drawer, and browser desktop alerts |

---

## 📂 Project Structure

```
warranty_system/
├── app.py                      # Main Streamlit application and component mounting
├── config.py                   # Central configuration, file paths, constants, thresholds
├── firebase_auth.py            # Firebase Identity Toolkit REST API & session provider
├── google_drive.py             # Google Drive API v3 client (Service Account read/write)
├── excel_database.py           # OpenPyXL database engine (4 sheets with thread-safe locking)
├── warranty_checker.py         # Dynamic warranty math, status calculations & de-duplication
├── notification_manager.py     # Notification orchestrator, unread badge counter, browser push
├── device_manager.py           # Device CRUD, ID generator, validation, duplicate prevention
├── reports.py                  # KPI analytics, styled Excel exporter, ReportLab PDF generator
├── test_system.py              # Automated test suite verifying all system components
├── requirements.txt            # Python dependencies
├── README.md                   # Complete documentation and setup manual
├── frontend/
│   ├── index.html              # Modern SaaS administrative interface
│   ├── style.css               # Clean SaaS styles, dark navy sidebar, rounded cards, modals
│   └── script.js               # Frontend controller, Chart.js graphs, Streamlit component bridge
├── assets/
│   └── logo.svg                # System vector shield logo
├── credentials/
│   ├── .gitkeep
│   ├── service_account.json.example   # Template for Google Drive Service Account
│   └── firebase_config.json.example   # Template for Firebase Web credentials
├── data/                       # Local Excel database cache
├── reports/                    # Generated PDF and Excel reports
└── .streamlit/
    └── config.toml             # Streamlit server and theme configurations
```

---

## 🔐 Credentials & Cloud Integration Setup

### 1. Google Drive API Setup (Service Account)

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (e.g. `device-warranty-system`).
3. Enable the **Google Drive API**:
   - Go to **APIs & Services > Library**.
   - Search for **Google Drive API** and click **Enable**.
4. Create a Service Account:
   - Go to **APIs & Services > Credentials**.
   - Click **Create Credentials > Service Account**.
   - Name it `device-warranty-sa` and grant the **Editor** role.
5. Create and download the JSON key:
   - Click on the created service account > **Keys** tab > **Add Key > Create new key > JSON**.
   - Save the downloaded file as `credentials/service_account.json` (or upload it via the Streamlit sidebar in the app).
6. *(Optional)* If you wish to store the database in a specific shared folder, share that folder with the service account email (e.g. `device-warranty-sa@...iam.gserviceaccount.com`) with **Editor** permissions.

### 2. Firebase Authentication Setup

1. Go to the [Firebase Console](https://console.firebase.google.com/).
2. Click **Add project** and follow the prompts.
3. In the left sidebar, navigate to **Build > Authentication**.
4. Click **Get Started** and enable the **Email/Password** sign-in provider.
5. In **Project Settings (General)**, scroll to **Your apps**, click the Web icon (`</>`), and register a web app.
6. Copy the `apiKey` and set it in your environment:
   ```bash
   export FIREBASE_WEB_API_KEY="AIzaSyYourFirebaseApiKey..."
   ```
   *Or enter it directly in the app sidebar under **Firebase Authentication**.*

---

## 🏃 Quick Start & Running the Application

### 1. Installation

Ensure Python 3.10+ is installed, then install dependencies:

```bash
pip install -r requirements.txt
```

### 2. Run the Automated System Audit

Verify database integrity, warranty mathematics, de-duplication, and PDF generation:

```bash
python warranty_system/test_system.py
```

### 3. Launch the Application

You can launch from the repository root:

```bash
streamlit run app.py
```

Or from within the `warranty_system/` directory:

```bash
streamlit run warranty_system/app.py
```

Open your browser at `http://localhost:8501`.

---

## 👥 Demo Logins for Instant Testing

When testing in local mode (or before entering Firebase API keys), you can sign in with one click using the built-in demo credentials:

| Role | Email | Password |
| :--- | :--- | :--- |
| **System Administrator** | `admin@equipguard.io` | `Password123!` |
| **IT Asset Manager** | `manager@equipguard.io` | `Password123!` |

*(The login screen also features 1-click quick evaluation buttons to auto-populate credentials).*

---

## 📊 Database Schema (Google Drive Excel Workbook)

The workbook `Device_Warranty_Database.xlsx` comprises 4 sheets:

### Sheet 1: `Devices`
| Column | Description |
| :--- | :--- |
| `Device_ID` | Sequential unique identifier (e.g., `DEV-1001`) |
| `Device_Name` | Equipment name and model (e.g., "MacBook Pro 16 M3 Max") |
| `Category` | One of: `Laptop`, `Desktop`, `Printer`, `Monitor`, `Router`, `CCTV`, `UPS`, `Mobile Phone`, `Other` |
| `Brand` | Hardware brand (Apple, Dell, HP, Cisco, Lenovo, etc.) |
| `Model_Number` | Hardware model string |
| `Serial_Number` | Unique serial number (searchable, duplicate-validated) |
| `Assigned_User` | Employee name or location |
| `Department` | Operating department (IT, Finance, HR, Operations, Sales, etc.) |
| `Purchase_Date` | Acquisition date (YYYY-MM-DD) |
| `Purchase_Price` | Acquisition cost |
| `Supplier` | Vendor / Supplier name |
| `Warranty_Start_Date` | Beginning of warranty coverage |
| `Warranty_End_Date` | Expiration date of warranty coverage |
| `Warranty_Duration_Months` | Calculated duration in months |
| `Invoice_Number` | Vendor billing invoice number |
| `Notes` | Freeform remarks and maintenance condition |
| `Image_URL` | Device thumbnail photo URL |
| `Created_At` | ISO 8601 registration timestamp |
| `Updated_At` | ISO 8601 last modified timestamp |

### Sheet 2: `Notifications`
| Column | Description |
| :--- | :--- |
| `Notification_ID` | Unique notification string (e.g., `NOTIF-781B7840`) |
| `Device_ID` | Associated device identifier |
| `Device_Name` | Hardware name |
| `Serial_Number` | Hardware serial number |
| `Milestone` | Alert milestone: `30_days`, `14_days`, `7_days`, `3_days`, `expired` |
| `Notification_Date` | Timestamp alert was generated |
| `Warranty_End_Date` | Expiry date of device |
| `Days_Remaining` | Remaining days at alert time |
| `Message` | Human-readable alert notification message |
| `Urgency` | Urgency rating: `critical`, `high`, `medium`, `low` |
| `Status` | `unread` or `read` |

### Sheet 3: `Activity_Log`
| Column | Description |
| :--- | :--- |
| `Log_ID` | Sequential audit record ID |
| `Timestamp` | ISO 8601 execution timestamp |
| `User_Email` | Email of user performing the action |
| `Action` | Action type (`Device Added`, `Device Updated`, `Device Deleted`, etc.) |
| `Device_ID` | Target hardware ID |
| `Details` | Contextual narrative of modifications |

### Sheet 4: `Settings`
| Column | Description |
| :--- | :--- |
| `Setting_Key` | Configuration property name |
| `Setting_Value` | Value string |
| `Description` | Explanation of configuration property |
| `Updated_At` | Timestamp of last modification |

---

## 🔔 Warranty Notification Engine & De-duplication

The engine dynamically evaluates warranties against the current system date:
- **Active**: More than 30 days remaining (`days > 30`)
- **Expiring Soon**: 30 days or fewer remaining (`0 <= days <= 30`)
- **Expired**: Warranty end date has passed (`days < 0`)

Milestone notifications are generated automatically:
1. **30 Days Before Expiration** (Milestone: `30_days`, Urgency: Low)
2. **14 Days Before Expiration** (Milestone: `14_days`, Urgency: Medium)
3. **7 Days Before Expiration** (Milestone: `7_days`, Urgency: High)
4. **3 Days Before Expiration** (Milestone: `3_days`, Urgency: Critical)
5. **On Expiration Date / Expired** (Milestone: `expired`, Urgency: Critical)

### De-duplication Guarantee
Before creating any alert, the system validates against existing entries in the `Notifications` sheet using a compound key `(Device_ID, Milestone)`. If an alert has already been generated for that specific device and milestone, it is skipped. This prevents notification spam across application reloads.

---

## ☁️ Deployment to Streamlit Community Cloud

To deploy to [Streamlit Community Cloud](https://streamlit.io/cloud):

1. Push this repository to GitHub (credentials are already ignored in `.gitignore`).
2. Go to **share.streamlit.io** and select your repository, branch, and entry point (`app.py`).
3. In **App Settings > Secrets**, configure your cloud secrets:
   ```toml
   FIREBASE_WEB_API_KEY = "AIzaSyYourFirebaseApiKey..."
   FIREBASE_PROJECT_ID = "your-firebase-project-id"

   # Paste the full contents of your Google Service Account JSON:
   GOOGLE_SERVICE_ACCOUNT_JSON = '''
   {
     "type": "service_account",
     "project_id": "your-project-id",
     "private_key_id": "...",
     "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
     "client_email": "device-warranty-sa@your-project-id.iam.gserviceaccount.com"
   }
   '''
   ```
4. Click **Deploy!** EquipGuard will boot up with automatic Google Drive synchronization and Firebase Authentication.

---

## 🔒 Security Best Practices

- **Zero Credential Exposure**: Service account keys and Firebase Admin private keys are never exposed in client-side HTML or JavaScript.
- **REST Authentication**: Firebase client operations use the standard public Identity Toolkit REST endpoint.
- **Strict Server Validation**: All device fields, serial uniqueness, and date ordering are validated on the backend.
- **Protected Database Updates**: Thread-safe database operations prevent concurrency race conditions during simultaneous updates.
