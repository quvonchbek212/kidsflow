# 🎒 KidsFlow — Modern Kindergarten Management ERP & Multi-Tenant SaaS Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14%20App%20Router-black.svg?style=flat&logo=next.js&logoColor=white)](https://nextjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0%2B-blue.svg?style=flat&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg?style=flat&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-Cache%20%26%20Queues-DC382D.svg?style=flat&logo=redis&logoColor=white)](https://redis.io)
[![aiogram](https://img.shields.io/badge/aiogram-3.x%20Telegram%20Bot-2CA5E0.svg?style=flat&logo=telegram&logoColor=white)](https://aiogram.dev)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?style=flat&logo=docker&logoColor=white)](https://docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A production-grade, multi-tenant enterprise management platform built specifically for private kindergartens, pre-schools, and early-childhood learning centers. Unifies daily attendance, child developmental progress, tuition billing, parent-teacher collaboration, and branch management into a unified, secure ecosystem.

---

## 🌟 Key Capabilities

### 1. 🏢 Multi-Tenant Branch & Role-Based Access Control (RBAC)
* **Isolated Branch Tenancy:** Complete data segmentation across multiple kindergarten campuses.
* **Security & Auth:** Argon2id password hashing, rotating JWT session management, and granular permission roles (`superadmin`, `branch_admin`, `teacher`, `accountant`, `parent`).
* **Audit Logging:** Comprehensive event traceability for student enrollments, fee adjustments, and security policy modifications.

### 2. 👶 Student & Guardian Operations
* **Lifecycle Management:** Child registration, medical profile management, emergency contact registry, and age-appropriate classroom placement.
* **Digital Attendance:** Real-time roll-call recording with instant notification alerts sent to parents.
* **Guardian Access:** Secure parent invitation workflows with phone-verified claim codes.

### 3. 📝 Activity Reports & Digital Portfolios
* **Draft-to-Publish Workflow:** Teachers create structured daily activity logs (meals, naps, curriculum activities, photos) and review before publishing.
* **Secure Storage:** Strict MIME-type validation, virus signature checks, and authenticated media URLs.

### 4. 💳 Automated Billing & Ledger Engine
* **Tuition Plans & Invoicing:** Automated recurring invoice generation based on enrollment schedules.
* **Idempotent Payments:** Robust payment reconciliation with allocation tracking, discount waivers, and debit/credit ledger auditability.

### 5. 🤖 Real-Time Parent Notifications & Telegram Bot
* **Transactional Outbox Architecture:** Background worker guarantees message delivery even during network dips.
* **Interactive Bot:** Allows parents to view daily meals, verify check-in/out timestamps, review invoices, and receive emergency announcements.

---

## 🏗 System Architecture

```text
                                  +---------------------------+
                                  |   Nginx Reverse Proxy     |
                                  |  (SSL, Rate Limiting)     |
                                  +-------------+-------------+
                                                |
                 +------------------------------+------------------------------+
                 |                                                             |
                 v                                                             v
+---------------------------------+                           +---------------------------------+
|   Frontend Web Portal           |                           |   Backend REST API Service      |
|   (Next.js 14, Tailwind CSS,    |                           |   (FastAPI, Async SQLAlchemy)   |
|    TypeScript, TanStack Query)  |                           +---------------+-----------------+
+---------------------------------+                                           |
                                                                              v
+---------------------------------+                           +---------------------------------+
|   Telegram Parent Bot           | <--- Outbox Worker Queue --- |  PostgreSQL 16 & Redis 7 Cache  |
|   (aiogram 3.x, Asyncio)        |                           |  (ACID Ledger, Session Cache)   |
+---------------------------------+                           +---------------------------------+
```

---

## 📂 Project Structure

```text
kidsflow/
├── backend/          # FastAPI async backend (Alembic, SQLAlchemy, Pydantic v2)
├── frontend-web/     # Next.js 14 App Router, TypeScript, modern UI dashboard
├── telegram-bot/     # aiogram 3.x async Telegram bot integration
├── nginx/            # Reverse proxy configurations and security headers
├── ci/               # CI/CD verification workflows and automated tests
└── docker-compose.yml
```

---

## 🚀 Quickstart

### Prerequisites
* Docker Engine 24+ and Docker Compose
* Node.js 18+ (for local frontend development)
* Python 3.11+ (for local backend development)

### 1. Launch with Docker Compose
```bash
# Clone the repository
git clone https://github.com/quvonchbek212/kidsflow.git
cd kidsflow

# Copy environment template
cp .env.example .env

# Start all microservices (Postgres, Redis, API, Frontend, Bot)
docker compose up -d --build
```

### 2. Verify Services
* **Backend API Docs:** `http://localhost:8000/docs`
* **Frontend Web Application:** `http://localhost:3000`
* **Health Endpoint:** `http://localhost:8000/health`

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).
