# 💸 Expense Platform

An AI-powered expense management platform built with **FastAPI**, **PostgreSQL**, and **Machine Learning**.

The application allows users to securely create accounts, authenticate using JWT, upload transaction data through CSV files, and automatically categorize their expenses using a trained machine-learning model.

## ✨ Features

* 🔐 User registration and authentication
* 🔑 JWT-based authentication
* 🔒 Password hashing with bcrypt
* 💳 Transaction management
* 📄 CSV transaction upload
* 🤖 Automatic expense categorization using Machine Learning
* 🗄️ PostgreSQL database
* ⚡ FastAPI REST API
* 🖥️ Built-in web interface
* 🚀 Render deployment configuration

## 🛠️ Tech Stack

* **Backend:** FastAPI
* **Language:** Python
* **Database:** PostgreSQL
* **ORM:** SQLAlchemy
* **Authentication:** JWT
* **Password Hashing:** Passlib / bcrypt
* **Machine Learning:** Scikit-learn
* **Data Processing:** Pandas
* **Server:** Uvicorn
* **Frontend:** HTML, CSS, JavaScript

## 📂 Project Structure

```text
expense-platform/
│
├── static/
│   ├── index.html
│   └── dashboard.html
│
├── auth.py
├── database.py
├── main.py
├── models.py
├── train_model.py
├── model.pkl
├── test_transactions.csv
├── requirements.txt
├── render.yaml
└── .gitignore
```

## 🚀 Getting Started

### Prerequisites

Make sure you have the following installed:

* Python 3.10+
* PostgreSQL
* Git
* pip

### 1. Clone the repository

```bash
git clone https://github.com/raffesabdelbassat/expense-platform.git
cd expense-platform
```

### 2. Create a virtual environment

**Windows**

```bash
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure PostgreSQL

Create a PostgreSQL database:

```sql
CREATE DATABASE expense_platform;
```

Configure your database connection in `database.py`.

> For production, use environment variables for database credentials and other secrets.

### 5. Run the application

```bash
uvicorn main:app --reload
```

The application will be available at:

```text
http://127.0.0.1:8000
```

## 📡 API Endpoints

| Method | Endpoint        | Authentication | Description              |
| ------ | --------------- | -------------- | ------------------------ |
| `GET`  | `/`             | ❌              | Open the web application |
| `POST` | `/register`     | ❌              | Register a new user      |
| `POST` | `/login`        | ❌              | Login and receive JWT    |
| `GET`  | `/me`           | ✅              | Get current user         |
| `POST` | `/upload`       | ✅              | Upload transactions CSV  |
| `GET`  | `/transactions` | ✅              | Get user transactions    |

## 📄 CSV Upload

Transactions can be uploaded using a CSV file.

Example:

```csv
date,description,amount
2026-01-01,Supermarket,45.50
2026-01-02,Electricity Bill,72.00
2026-01-03,Coffee Shop,5.50
```

When transactions are uploaded, the machine-learning model analyzes the description and automatically predicts a category.

Example:

```text
Supermarket Purchase → Food
Uber Ride             → Transport
Electricity Bill      → Utilities
```

## 🤖 Machine Learning

The project includes a trained machine-learning model stored in:

```text
model.pkl
```

The training process is implemented in:

```text
train_model.py
```

The model uses transaction descriptions to predict appropriate expense categories.

## 🔐 Authentication

The API uses **JWT (JSON Web Tokens)** to protect authenticated endpoints.

After logging in, include the token in requests:

```http
Authorization: Bearer <your-token>
```

## 🗄️ Database

The application uses PostgreSQL with SQLAlchemy.

### User

```text
id
email
hashed_password
```

### Transaction

```text
id
user_id
date
description
amount
category
```

Each transaction is associated with the user who uploaded it.

## 🌐 Deployment

The repository includes a `render.yaml` configuration for deployment with **Render**.

For production deployment, configure your environment variables securely and use a managed PostgreSQL database.

## 🔒 Security

Before deploying the application publicly:

* Store database credentials in environment variables.
* Store JWT secrets in environment variables.
* Never commit passwords or secrets to GitHub.
* Use HTTPS in production.
* Validate uploaded CSV files.
* Add appropriate input validation and request limits.

## 🔮 Future Improvements

* 📊 Expense analytics and charts
* 💰 Budget management
* 📅 Monthly and yearly expense reports
* 🔎 Transaction search and filtering
* 🏷️ Custom categories
* 📤 Export transactions
* 🔔 Budget notifications
* 📱 Improved mobile interface
* 🐳 Docker support
* 🧪 Automated tests
* 🔄 Database migrations with Alembic

## 🤝 Contributing

Contributions are welcome!

1. Fork the repository.
2. Create a new branch:

```bash
git checkout -b feature/my-feature
```

3. Make your changes.
4. Commit your changes:

```bash
git commit -m "Add my feature"
```

5. Push your branch:

```bash
git push origin feature/my-feature
```

6. Open a Pull Request.

## 📜 License

No license has currently been specified for this project.

## 👨‍💻 Author

**Raffes Abdelbassat**

GitHub: [@raffesabdelbassat](https://github.com/raffesabdelbassat)

---

⭐ If you find this project useful, consider giving it a star!

**Built with Python, FastAPI, PostgreSQL & Machine Learning.**
