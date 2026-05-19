# LMS - Online Learning Platform Backend

A complete, production-ready, asynchronous REST API backend for an Online Learning Platform built with **Python FastAPI**, **MongoDB (Motor)**, **JWT Authentication**, and **Razorpay payment integration**.

Designed with **Clean Architecture** patterns (routers, services, validation schemas, middlewares, database connectors, and utility helpers), this backend is fully optimized for horizontal scaling and is ready to integrate out-of-the-box with a frontend framework like React.

---

## 🚀 Key Features

*   **Secure Authentication**: Standard JWT Access & Refresh Token architecture with secure direct `bcrypt` password hashing (clean of passlib deprecation warnings).
*   **Role-Based Access Control (RBAC)**: Secure access restriction for `Student`, `Instructor`, and `Admin` roles across protected routes.
*   **Forgot Password Simulation**: Seamless OTP-based password recovery. During development, simulated 6-digit OTP codes are logged to the console and returned in responses for instant testing!
*   **Rich Course Management**: Full CRUD operations for Courses, Sections, and Lessons. Features dynamic filtering, pagination, sorting, full-text regex search, and dynamic ratings calculations.
*   **Nested GraphQL-like Populated Responses**: Retrieve a course with its sections and lessons sorted and nested inside a single database-efficient, aggregate API call.
*   **Razorpay Payment Checkout**: Full checkout order creation and cryptographic web signature verification. Includes a **built-in simulated payment engine**: if default sandbox API keys are detected, the platform safely simulates successful checkouts, allowing end-to-end checkout runs without configuring real merchant accounts!
*   **Progress Tracking & Wishlists**: Track student lecture completion dynamically (updating progress percentages on active course enrollments) and allow bookmarking courses.
*   **Instructor Dashboard**: Custom dashboard calculations aggregation (courses list, active students count, cumulative revenue sums, average ratings, and recent enrollment activity feeds).
*   **Administrator Management Suite**: Deactivate/ban user profiles, view full system transactional histories with student/course relationships, delete users, and administratively drop courses for violations.
*   **Production Safeguards**: Global exception handlers (mapping stack traces to clean JSON payloads), in-memory IP Rate Limiting middleware, CORS setups, and automatic static media asset storage.

---

## 🛠️ Tech Stack

*   **Backend Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Asynchronous, Type-safe python framework)
*   **Database**: [MongoDB](https://www.mongodb.com/) (High-performance Document Database)
*   **Database Async Driver**: [Motor](https://motor.readthedocs.io/) (Asynchronous MongoDB Client)
*   **Authentication**: JWT Access & Refresh tokens via [python-jose](https://github.com/mpdavy/python-jose)
*   **Password Hashing**: Direct [bcrypt](https://github.com/pyca/bcrypt/) integration
*   **Payment Gateway**: [Razorpay Python SDK](https://github.com/razorpay/razorpay-python)
*   **Validation**: [Pydantic v2](https://docs.pydantic.dev/) (Data serialization and schemas parsing)
*   **Environment Manager**: [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) & `python-dotenv`

---

## 📂 Folder Structure

The project strictly follows a scalable clean-architecture structure:

```text
Online-Learning-Platform/
├── 
│   ├── config/              # Environment configurations & settings loading
│   │   └── config.py
│   ├── database/            # MongoDB connection logic and collections getters
│   │   └── mongodb.py
│   ├── middleware/          # Protected routes auth dependencies & rate limiter
│   │   ├── auth.py
│   │   └── rate_limit.py
│   ├── schemas/             # Pydantic request/response validation schemas
│   │   ├── user.py
│   │   ├── course.py
│   │   ├── section.py
│   │   ├── lesson.py
│   │   ├── payment.py
│   │   ├── enrollment.py
│   │   ├── progress.py
│   │   ├── wishlist.py
│   │   └── category.py
│   ├── services/            # Decoupled business logic controllers
│   │   ├── auth_service.py
│   │   ├── course_service.py
│   │   ├── student_service.py
│   │   ├── instructor_service.py
│   │   └── admin_service.py
│   ├── routers/             # HTTP Route handlers
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── course.py
│   │   ├── payment.py
│   │   ├── enrollment.py
│   │   ├── review.py
│   │   ├── wishlist.py
│   │   ├── instructor.py
│   │   └── admin.py
│   ├── utils/               # Hashing, JWT utils & DB formatting serializations
│   │   ├── security.py
│   │   └── db_helpers.py
│   └── main.py              # Application entrypoint & middlewares configuration
├── uploads/                 # Local directory for user file uploads (thumbnails/videos)
├── .env                     # Local environment variables
├── .env.example             # Template environment variables
├── requirements.txt         # Package dependencies
├── postman_collection.json  # Pre-configured Postman JSON Collection
└── README.md                # Setup and documentation
```

---

## ⚙️ Getting Started & Installation

### 1. Prerequisites
*   Python 3.10 or higher (Python 3.14 recommended/tested)
*   MongoDB running locally (`mongodb://localhost:27017`) or a remote MongoDB Atlas connection string.

### 2. Clone and Setup Environment
Navigate to the directory and ensure that `.env` is loaded with correct local database parameters:
```bash
# Clone the repository
git clone https://github.com/anash06/Online-Learning-Platform.git
cd Online-Learning-Platform
```

### 3. Initialize Virtual Environment & Install Requirements
We utilize a virtual environment to manage dependencies locally:
```powershell
# Create virtual environment
python -m venv venv

# Activate on Windows Powershell
.\venv\Scripts\Activate.ps1
# (On macOS/Linux: source venv/bin/activate)

# Install backend dependencies
pip install -r requirements.txt
```

### 4. Run the Server
Startup the uvicorn asynchronous development server:
```bash
uvicorn main:app --reload --port 8000
```
Upon startup, the console will print:
*   `Connecting to MongoDB...`
*   `Connected to MongoDB successfully!`
*   `Database empty of categories. Seeding default list...` (Auto-seeds default categories!)
*   `Successfully seeded 5 default course categories.`

---

## 🧪 Interactive API Documentation & Test Flow

### Swagger / OpenAPI Integration
The platform comes equipped with interactive auto-documentation. Navigate to:
👉 **[http://localhost:8000/docs](http://localhost:8000/docs)** to access the beautiful interactive Swagger dashboard where you can make requests directly!

### Developer Testing Utilities (Console Logs)
1.  **Simulated Forgot Password**: Make a request to `/api/v1/auth/forgot-password`. Check your backend terminal console log! It will log a stylized simulated email frame printing the active 6-digit OTP code to verify instantly!
2.  **Simulated Razorpay Checkouts**: By default, the app initializes mock payments for sandbox checkouts. When calling `/payments/create-order` and `/payments/verify-signature`, you don't need real merchant keys; simulated signatures will successfully authenticate!

### Importing Postman Collection
A fully populated Postman collection is generated for you.
1.  Open Postman.
2.  Click **Import** in the top bar.
3.  Select the **`postman_collection.json`** file in this project's root folder.
4.  It will populate a folder `LMS - Online Learning Platform` containing categorized API requests with pre-configured Bearer token scopes!

---

## 🔗 Primary REST APIs Schema

| Module | Endpoint | Method | Role | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Auth** | `/api/v1/auth/signup` | POST | Public | Register user account |
| **Auth** | `/api/v1/auth/login` | POST | Public | Get Access & Refresh tokens |
| **Auth** | `/api/v1/auth/forgot-password`| POST | Public | Request simulated reset OTP |
| **Auth** | `/api/v1/auth/reset-password` | POST | Public | Verify OTP and reset password |
| **User** | `/api/v1/users/me` | GET | Authenticated| Fetch logged user details |
| **Courses**| `/api/v1/courses/` | GET | Public | Search/filter/list courses |
| **Courses**| `/api/v1/courses/{id}` | GET | Public | Fetch populated Course tree |
| **Courses**| `/api/v1/courses/` | POST | Instructor | Create new course draft |
| **Courses**| `/api/v1/courses/{id}` | PUT | Instructor | Update course settings |
| **Courses**| `/api/v1/courses/{id}/sections`| POST| Instructor | Add course syllabus section |
| **Courses**| `/api/v1/courses/{id}/upload-thumbnail`| POST | Instructor | Upload local course banner image|
| **Payments**| `/api/v1/payments/create-order`| POST | Authenticated| Checkout (Free / Razorpay) |
| **Payments**| `/api/v1/payments/verify-signature`|POST| Authenticated| Confirm payment & enroll |
| **Enrolls**| `/api/v1/enrollments/` | GET | Student | Get purchased courses |
| **Enrolls**| `/api/v1/enrollments/{id}/progress`| PUT | Student | Mark lesson complete |
| **Instructor**|`/api/v1/instructor/dashboard`| GET | Instructor | Fetch analytics dashboard stats|
| **Admin** | `/api/v1/admin/stats` | GET | Admin | Global system ledger and metrics|
| **Admin** | `/api/v1/admin/users` | GET | Admin | Management & listing of user profiles|

---

## 🔒 Security Best Practices

1.  **Strict Token Scopes**: Tokens store specific user IDs and roles. Middleware dependencies restrict sensitive content to the necessary user tier.
2.  **No Plaintext Hashing**: Passwords undergo dynamic hashing with salt using standard `bcrypt` algorithms.
3.  **Sanitized Outputs**: Database primary keys are safely formatted, and Pydantic schemas filter sensitive password variables from responses.
4.  **Middleware Defense**: IP-based Rate Limiter guards endpoints, and CORS controls resource sharing vectors.