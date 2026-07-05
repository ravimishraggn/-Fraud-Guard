# FraudGuard — Build Roadmap

## Legend
- [x] Done
- [~] In progress
- [ ] Not started

## Phase 1 — Project Foundation
- [x] Monorepo structure created
- [x] Docker Compose with all services
- [x] PostgreSQL schema and migrations
- [x] Redis queue setup
- [x] MinIO local file storage
- [x] Environment variables and secrets

## Phase 2 — Backend Core (FastAPI)
- [x] Project bootstrap with FastAPI
- [x] Database models (SQLAlchemy)
- [x] Authentication (JWT + RBAC)
- [x] Document upload API
- [x] File storage service (MinIO)
- [x] Background task queue (Celery + Redis)
- [x] OCR service (PaddleOCR)
- [x] AI extraction service (OpenAI GPT-4o-mini)
- [x] Fraud detection engine (5 core checks)
- [x] GSTIN verification service
- [x] Notification service (email)
- [x] REST API documentation (auto Swagger)

## Phase 3 — Frontend (Next.js)
- [ ] Next.js project with TypeScript + Tailwind
- [ ] Authentication pages (login, register)
- [ ] Dashboard — owner view (KPIs, savings)
- [ ] Upload screen — drag and drop + WhatsApp hint
- [ ] Review queue — flagged invoices list
- [ ] Invoice detail — extracted fields + fraud flags
- [ ] Vendor list — whitelist management
- [ ] Rules configuration — custom fraud rules
- [ ] Settings — team, notifications, limits

## Phase 4 — Integration and Testing
- [ ] Frontend connected to backend APIs
- [ ] End-to-end flow working (upload → extract → flag → review)
- [ ] Sample data seeder (demo invoices including fraudulent ones)
- [ ] Health check endpoints

## Phase 5 — Infrastructure
- [ ] Terraform: AWS VPC + EKS skeleton
- [ ] Terraform: RDS PostgreSQL
- [ ] Terraform: ElastiCache Redis
- [ ] Terraform: S3 bucket
- [ ] Terraform: ECR for Docker images
- [ ] Dockerfile for each service
- [ ] GitHub Actions CI/CD skeleton

## Current Status
Last updated: 2026-07-04
Currently working on: Phase 3 — Next.js frontend
