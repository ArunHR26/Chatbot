# 🚀 Cloud-Native RAG

<div align="center">

**A Production-Ready, Kubernetes-Native Retrieval-Augmented Generation Application**

[![Next.js](https://img.shields.io/badge/Next.js-14-black?style=for-the-badge&logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-Ready-326CE5?style=for-the-badge&logo=kubernetes&logoColor=white)](https://kubernetes.io/)
[![Docker](https://img.shields.io/badge/Docker-Multi--Arch-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Helm](https://img.shields.io/badge/Helm-Chart-0F1689?style=for-the-badge&logo=helm&logoColor=white)](https://helm.sh/)

*Upload documents. Ask questions. Get AI-powered answers with source citations.*

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Quick Start](#-quick-start)
- [API Reference](#-api-reference)
- [Configuration](#-configuration)
- [Kubernetes Deployment](#-kubernetes-deployment)
- [Development](#-development)
- [Contributing](#-contributing)

---

> [!CAUTION]
> ## ⚠️ Production Requirements
> 
> **This application requires the following security hardening before production deployment:**
> 
> ### Security
> - [ ] **External Secrets**: Replace plain-text API keys with External Secrets Operator (ESO) + HashiCorp Vault/AWS Secrets Manager
> - [ ] **CORS Restriction**: Change `allow_origins=["*"]` to specific domains in `backend/app/main.py`
> - [ ] **Rate Limiting**: Add [SlowAPI](https://github.com/laurentS/slowapi) middleware to prevent abuse
> - [ ] **Input Sanitization**: Add content validation for uploaded files (magic bytes, virus scanning)
> - [ ] **SQL Injection**: Replace raw SQL in `services.py` similarity search with parameterized ORM queries
> 
> ### Database
> - [ ] **Credentials**: Generate random PostgreSQL passwords per deployment (not `postgres:postgres`)
> - [ ] **Migrations**: Implement [Alembic](https://alembic.sqlalchemy.org/) for versioned schema migrations
> - [ ] **Connection Pooling**: Add [PgBouncer](https://www.pgbouncer.org/) sidecar for production workloads
> - [ ] **Backup Strategy**: Configure CronJob for `pg_dump` to S3/GCS
> - [ ] **High Availability**: Consider [CloudNativePG](https://cloudnative-pg.io/) operator or managed PostgreSQL
> 
> See the [Security Hardening Guide](#security-hardening) section for implementation details.

---

Cloud-Native RAG is a complete Retrieval-Augmented Generation (RAG) solution designed for cloud-native environments. It enables users to:

1. **📄 Upload PDF Documents** - Drag-and-drop interface for knowledge base ingestion
2. **🔍 Semantic Search** - Vector similarity search using pgvector
3. **💬 Conversational AI** - Chat with your documents using any LLM via OpenRouter
4. **📱 Modern UI** - ChatGPT-style interface with streaming responses

### Key Features

| Feature                | Description                                                                    |
| ---------------------- | ------------------------------------------------------------------------------ |
| **Document Ingestion** | Upload PDFs with automatic text extraction, chunking, and embedding generation |
| **Vector Search**      | Semantic similarity search using PostgreSQL with pgvector extension            |
| **Streaming Chat**     | Real-time streaming responses with Server-Sent Events (SSE)                    |
| **Source Citations**   | Every response includes references to source documents                         |
| **Kubernetes Native**  | Complete Helm chart with StatefulSets, PVCs, HPA, PDB                          |
| **Multi-Architecture** | Docker images support both ARM64 and AMD64                                     |

---

## 🏗 Architecture

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              KUBERNETES CLUSTER                                  │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │                              INGRESS (nginx)                                │ │
│  │                        rag.yourdomain.com                                   │ │
│  └─────────────────────────────┬──────────────────────────────────────────────┘ │
│                                │                                                 │
│            ┌───────────────────┴───────────────────┐                            │
│            │                                       │                            │
│            ▼                                       ▼                            │
│  ┌─────────────────────┐              ┌─────────────────────┐                   │
│  │    FRONTEND POD     │              │    BACKEND POD      │                   │
│  │  ┌───────────────┐  │              │  ┌───────────────┐  │                   │
│  │  │   Next.js 14  │  │    REST/SSE  │  │   FastAPI     │  │                   │
│  │  │  (React 18)   │◄─┼──────────────┼─►│   (Python)    │  │                   │
│  │  │  Tailwind CSS │  │              │  │   Async I/O   │  │                   │
│  │  └───────────────┘  │              │  └───────┬───────┘  │                   │
│  │    Port: 3000       │              │          │          │                   │
│  └─────────────────────┘              │          │ asyncpg  │                   │
│                                       │          ▼          │                   │
│                                       │  ┌───────────────┐  │                   │
│                                       │  │   pgvector    │  │                   │
│                                       │  │   embeddings  │  │                   │
│                                       │  └───────────────┘  │                   │
│                                       │    Port: 8000       │                   │
│                                       └──────────┬──────────┘                   │
│                                                  │                              │
│                                                  ▼                              │
│                               ┌─────────────────────────────────┐               │
│                               │      POSTGRESQL STATEFULSET      │               │
│                               │  ┌─────────────────────────────┐ │               │
│                               │  │   PostgreSQL 16 + pgvector  │ │               │
│                               │  │   Vector similarity search  │ │               │
│                               │  └─────────────────────────────┘ │               │
│                               │  ┌─────────────────────────────┐ │               │
│                               │  │   PersistentVolumeClaim     │ │               │
│                               │  │        (10Gi default)       │ │               │
│                               │  └─────────────────────────────┘ │               │
│                               │         Port: 5432              │               │
│                               └─────────────────────────────────┘               │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         │ HTTPS
                                         ▼
                              ┌─────────────────────┐
                              │   OPENROUTER API    │
                              │  (LLM & Embeddings) │
                              │                     │
                              │  • GPT-4o-mini      │
                              │  • text-embedding   │
                              │    -3-small         │
                              └─────────────────────┘
```

### RAG Pipeline Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   PDF File   │────►│   Extract    │────►│    Chunk     │────►│   Generate   │
│   Upload     │     │    Text      │     │    Text      │     │  Embeddings  │
│              │     │  (PyPDF2)    │     │ (1000 chars) │     │ (OpenRouter) │
└──────────────┘     └──────────────┘     └──────────────┘     └──────┬───────┘
                                                                       │
                                                                       ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Stream     │◄────│   Generate   │◄────│   Retrieve   │◄────│    Store     │
│   Response   │     │   Response   │     │   Context    │     │   Vectors    │
│   (SSE)      │     │  (LLM API)   │     │ (Top-K=5)    │     │  (pgvector)  │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

### Data Flow Diagram

```
                           DOCUMENT INGESTION FLOW
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│    User                 Frontend                Backend               DB    │
│     │                      │                       │                   │    │
│     │──── Upload PDF ─────►│                       │                   │    │
│     │                      │                       │                   │    │
│     │                      │── POST /api/ingest ──►│                   │    │
│     │                      │      (multipart)      │                   │    │
│     │                      │                       │── Extract Text ───┤    │
│     │                      │                       │── Split Chunks ───┤    │
│     │                      │                       │                   │    │
│     │                      │                       │── Call OpenRouter─┼──► │
│     │                      │                       │   (Embeddings)    │    │
│     │                      │                       │◄──────────────────┤    │
│     │                      │                       │                   │    │
│     │                      │                       │── INSERT chunks ──►│    │
│     │                      │                       │   with vectors    │    │
│     │                      │                       │                   │    │
│     │                      │◄── { success: true } ─┤                   │    │
│     │◄─── Show Success ────┤                       │                   │    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

                              CHAT QUERY FLOW
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│    User                 Frontend                Backend               DB    │
│     │                      │                       │                   │    │
│     │──── Ask Question ───►│                       │                   │    │
│     │                      │                       │                   │    │
│     │                      │── POST /api/chat ────►│                   │    │
│     │                      │   (JSON body)         │                   │    │
│     │                      │                       │── Embed Query ────┼──► │
│     │                      │                       │   (OpenRouter)    │    │
│     │                      │                       │◄──────────────────┤    │
│     │                      │                       │                   │    │
│     │                      │                       │── Vector Search ──►│    │
│     │                      │                       │   (Top 5 chunks)  │    │
│     │                      │                       │◄─── Results ──────┤    │
│     │                      │                       │                   │    │
│     │                      │◄─ SSE: sources ───────┤                   │    │
│     │◄── Show Sources ─────┤                       │                   │    │
│     │                      │                       │── Stream from ────┼──► │
│     │                      │◄─ SSE: content chunks │   OpenRouter LLM  │    │
│     │◄── Render Markdown ──┤        (loop)        │◄──────────────────┤    │
│     │                      │                       │                   │    │
│     │                      │◄─ SSE: done ──────────┤                   │    │
│     │◄── Complete ─────────┤                       │                   │    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠 Tech Stack

### Frontend

| Technology         | Version | Purpose                         |
| ------------------ | ------- | ------------------------------- |
| **Next.js**        | 14.1    | React framework with App Router |
| **React**          | 18.2    | UI library                      |
| **Tailwind CSS**   | 3.4     | Utility-first CSS framework     |
| **Lucide React**   | 0.323   | Icon library                    |
| **react-markdown** | 9.0     | Markdown rendering              |
| **TypeScript**     | 5.3     | Type safety                     |

### Backend

| Technology   | Version | Purpose                    |
| ------------ | ------- | -------------------------- |
| **FastAPI**  | 0.109   | Async Python web framework |
| **SQLModel** | 0.0.14  | SQL databases + Pydantic   |
| **asyncpg**  | 0.29    | Async PostgreSQL driver    |
| **pgvector** | 0.2.4   | Vector similarity search   |
| **PyPDF2**   | 3.0     | PDF text extraction        |
| **httpx**    | 0.26    | Async HTTP client          |
| **uvicorn**  | 0.27    | ASGI server                |

### Infrastructure

| Technology        | Version | Purpose                    |
| ----------------- | ------- | -------------------------- |
| **PostgreSQL**    | 16      | Database with pgvector     |
| **Docker**        | -       | Containerization           |
| **Kubernetes**    | 1.25+   | Container orchestration    |
| **Helm**          | 3.x     | Kubernetes package manager |
| **nginx-ingress** | -       | Ingress controller         |

---

## 📁 Project Structure

```
Cloud-Native-RAG/
│
├── 📂 backend/                      # FastAPI Backend Service
│   ├── 📂 app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app, routes, middleware
│   │   ├── config.py               # Pydantic settings from env
│   │   ├── database.py             # Async SQLAlchemy engine & session
│   │   ├── models.py               # SQLModel ORM definitions
│   │   └── services.py             # Business logic (PDF, embeddings, chat)
│   ├── requirements.txt            # Python dependencies
│   └── Dockerfile                  # Multi-stage Python 3.11 slim
│
├── 📂 frontend/                     # Next.js Frontend Application
│   ├── 📂 public/
│   │   ├── favicon.svg
│   │   └── manifest.json
│   ├── 📂 src/
│   │   ├── 📂 app/
│   │   │   ├── globals.css         # Tailwind + custom styles
│   │   │   ├── layout.tsx          # Root layout with metadata
│   │   │   └── page.tsx            # Main chat interface
│   │   ├── 📂 components/
│   │   │   ├── ChatMessage.tsx     # Message bubble with Markdown
│   │   │   └── FileUpload.tsx      # Drag-and-drop upload zone
│   │   └── 📂 lib/
│   │       └── api.ts              # API client with streaming
│   ├── package.json
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── next.config.js
│   └── Dockerfile                  # Multi-stage Node 18 Alpine
│
├── 📂 charts/                       # Helm Charts
│   └── 📂 rag-stack/
│       ├── Chart.yaml              # Chart metadata
│       ├── values.yaml             # Default configuration
│       └── 📂 templates/
│           ├── _helpers.tpl        # Template helpers
│           ├── configmap.yaml      # Non-sensitive config
│           ├── secret.yaml         # API keys, passwords
│           ├── serviceaccount.yaml
│           ├── deployment-backend.yaml
│           ├── deployment-frontend.yaml
│           ├── statefulset-db.yaml # PostgreSQL with PVC
│           ├── service.yaml        # ClusterIP services
│           ├── ingress.yaml        # External access
│           ├── hpa.yaml            # Horizontal Pod Autoscaler
│           ├── pdb.yaml            # Pod Disruption Budget
│           └── NOTES.txt           # Post-install instructions
│
├── docker-compose.yml              # Local development stack
├── .env.example                    # Environment template
├── .gitignore
└── README.md                       # This file
```

---

## 🚀 Quick Start

### Prerequisites

- **Docker** & **Docker Compose** (v2.x+)
- **OpenRouter API Key** ([Get one here](https://openrouter.ai/))
- For Kubernetes: **kubectl**, **Helm 3.x**, and a cluster

### Option 1: Docker Compose (Recommended for Development)

```bash
# 1. Clone the repository
git clone https://github.com/ArunHR26/Chatbot.git
cd Chatbot

# 2. Configure environment
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY

# 3. Start all services
docker-compose up -d

# 4. Check status
docker-compose ps

# 5. Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Option 2: Kubernetes with Helm

```bash
# 1. Create namespace
kubectl create namespace rag

# 2. Create values override
cat > my-values.yaml << 'EOF'
openrouter:
  apiKey: "sk-or-v1-your-api-key-here"

ingress:
  enabled: true
  hosts:
    - host: rag.mycompany.com
      paths:
        - path: /
          pathType: Prefix
          service: frontend
        - path: /api
          pathType: Prefix
          service: backend
EOF

# 3. Install the chart
helm install rag-stack ./charts/rag-stack \
  --namespace rag \
  -f my-values.yaml

# 4. Watch deployment
kubectl get pods -n rag -w
```

---

## 📡 API Reference

### Health Endpoints

| Endpoint  | Method | Description                                    |
| --------- | ------ | ---------------------------------------------- |
| `/health` | GET    | Liveness probe - returns if service is running |
| `/ready`  | GET    | Readiness probe - verifies database connection |

### Document Endpoints

#### Upload Document
```http
POST /api/ingest
Content-Type: multipart/form-data

file: <PDF file>
```

**Response:**
```json
{
  "success": true,
  "document_id": "uuid",
  "filename": "document.pdf",
  "chunks_created": 42,
  "message": "Successfully ingested document.pdf with 42 chunks"
}
```

#### List Documents
```http
GET /api/documents
```

**Response:**
```json
{
  "documents": [
    {
      "id": "uuid",
      "name": "document.pdf",
      "created_at": "2024-01-15T10:30:00Z",
      "chunks": 42
    }
  ],
  "total": 1
}
```

### Chat Endpoints

#### Send Message (Streaming)
```http
POST /api/chat
Content-Type: application/json

{
  "message": "What is this document about?",
  "history": [
    {"role": "user", "content": "Previous question"},
    {"role": "assistant", "content": "Previous answer"}
  ]
}
```

**Response (Server-Sent Events):**
```
data: {"type": "sources", "data": ["doc1.pdf", "doc2.pdf"]}

data: {"type": "content", "data": "Based on"}
data: {"type": "content", "data": " the documents"}
data: {"type": "content", "data": "..."}

data: {"type": "done"}
```

---

## ⚙ Configuration

### Environment Variables

| Variable              | Required | Default                         | Description                  |
| --------------------- | -------- | ------------------------------- | ---------------------------- |
| `OPENROUTER_API_KEY`  | ✅ Yes    | -                               | Your OpenRouter API key      |
| `DATABASE_URL`        | No       | `postgresql+asyncpg://...`      | PostgreSQL connection string |
| `OPENROUTER_BASE_URL` | No       | `https://openrouter.ai/api/v1`  | OpenRouter API base URL      |
| `OPENROUTER_MODEL`    | No       | `openai/gpt-4o-mini`            | LLM model for chat           |
| `EMBEDDING_MODEL`     | No       | `openai/text-embedding-3-small` | Embedding model              |
| `EMBEDDING_DIMENSION` | No       | `1536`                          | Vector dimension             |
| `CHUNK_SIZE`          | No       | `1000`                          | Characters per chunk         |
| `CHUNK_OVERLAP`       | No       | `200`                           | Overlap between chunks       |

### Helm Values

See full configuration in [`charts/rag-stack/values.yaml`](./charts/rag-stack/values.yaml)

Key configurations:

```yaml
# Required
openrouter:
  apiKey: "your-key"

# Scaling
backend:
  replicaCount: 2
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 10

# Storage
postgresql:
  persistence:
    size: 50Gi
    storageClass: "gp3"
```

---

## ☸ Kubernetes Deployment

### Architecture in Kubernetes

```
┌─────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                    │
│                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │  Ingress    │  │   Service   │  │    Service      │  │
│  │  Controller │  │  (Backend)  │  │   (Frontend)    │  │
│  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘  │
│         │                │                   │           │
│         ▼                ▼                   ▼           │
│  ┌─────────────────────────────────────────────────────┐│
│  │              Deployments / StatefulSets              ││
│  │  ┌─────────┐  ┌─────────┐  ┌─────────────────────┐  ││
│  │  │Backend  │  │Frontend │  │    PostgreSQL       │  ││
│  │  │ Pod x2  │  │ Pod x2  │  │   StatefulSet x1    │  ││
│  │  └─────────┘  └─────────┘  └──────────┬──────────┘  ││
│  │                                       │              ││
│  │                              ┌────────▼────────┐    ││
│  │                              │       PVC       │    ││
│  │                              │   (10Gi data)   │    ││
│  │                              └─────────────────┘    ││
│  └─────────────────────────────────────────────────────┘│
│                                                          │
│  ┌─────────────────────────────────────────────────────┐│
│  │                    ConfigMaps & Secrets              ││
│  │  • rag-stack-backend-config (ConfigMap)              ││
│  │  • rag-stack-secrets (Secret - API keys)             ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

### Useful Commands

```bash
# View all resources
kubectl get all -l app.kubernetes.io/instance=rag-stack -n rag

# View logs
kubectl logs -l app.kubernetes.io/component=backend -n rag -f
kubectl logs -l app.kubernetes.io/component=frontend -n rag -f

# Scale backend
kubectl scale deployment rag-stack-backend --replicas=5 -n rag

# Connect to PostgreSQL
kubectl exec -it rag-stack-postgresql-0 -n rag -- psql -U postgres -d ragdb

# Port forward for local access
kubectl port-forward svc/rag-stack-frontend 3000:3000 -n rag
```

---

## 🔧 Development

### Backend Development

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Run with hot reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

### Building Docker Images

```bash
# Build for local platform
docker build -t rag-backend:dev ./backend
docker build -t rag-frontend:dev ./frontend

# Build for multiple architectures (CI/CD)
docker buildx build --platform linux/amd64,linux/arm64 \
  -t ghcr.io/yourorg/rag-backend:1.0.0 \
  --push ./backend
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built with ❤️ for the Cloud-Native Community**

</div>
