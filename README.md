# Spring Boot REST API Template

This is a basic REST API template built with Spring Boot, using an H2 in-memory database. It demonstrates typical structure, including layers for controller, service, repository, and entity.

This project now includes integrated security scanning (Trivy, Docker Scout, Snyk, Gitleaks) and an AI-assisted STRIDE threat model review in CI/CD.

### 🔒 Security Scans in CI/CD
- **Trivy**: Scans the application JAR and Docker image for known vulnerabilities (CVEs) in OS packages and dependencies.
- **Docker Scout**: Disabled by default because it requires a GitHub Pro/Team account. Users can enable it by granting the `GITHUB_TOKEN` `write` permissions to contents and pull-requests in the repo settings or using a PAT.
- **Snyk**: Performs deep dependency scanning (both OS and app-level) and license compliance checks.
- **Gitleaks**: Detects secrets and sensitive information in the codebase.

### 🤖 AI-Assisted STRIDE Threat Review
Every pull request and push triggers an automated AI-based threat modeling process using the STRIDE framework:
- Collects code diffs, architecture documentation, and project structure.
- Prompts an AI model to analyze potential security threats in the change set.
- Generates a Markdown report uploaded as a build artifact (and posted to PRs) to guide secure coding practices.

### 📊 ELK Stack Integration for Log Management
This project now includes local development support for the ELK stack — Elasticsearch, Logstash, and Kibana — to enable log aggregation and visualization.

- **Starting ELK**: Run the ELK stack locally using the provided Docker Compose file:
  ```bash
  docker-compose -f docker-compose.elk.yml up
  ```
- **Logstash Configuration** (`logstash.conf`):
  - Listens on TCP port `5001` for JSON lines formatted logs from Logback.
  - Includes an optional mutate filter to rename the `logger_name` field to `logger`.
  - Outputs logs to Elasticsearch with an index pattern `springboot-logs-YYYY.MM.dd`.
  - Also outputs logs to stdout for debugging purposes.
- **Kibana Usage**:
  - Access Kibana UI at [http://localhost:5601](http://localhost:5601).
  - Create a Data View for the index pattern `springboot-logs-*` and set `@timestamp` as the time filter field.
  - Use Kibana to build dashboards and visualize logs effectively.
- **Development Mode**:
  - When running the Spring Boot application in development mode, logs are automatically sent to Logstash, enabling real-time log aggregation and analysis.

### 🧠 Streamlit UI for Natural Language Log Queries
This project now includes an AI-powered Streamlit UI that allows you to query Elasticsearch logs using natural language. The interface supports switching between Elasticsearch SQL (ESQL) and Domain Specific Language (DSL) queries, displays the generated query, and shows the results in a user-friendly table format.

**Running the Streamlit Log Query UI:**

1. Start the backend API server using Uvicorn:
   ```bash
   uvicorn log_query_backend:app --reload --host 0.0.0.0 --port 8000
   ```

2. In a separate terminal, launch the Streamlit frontend:
   ```bash
   streamlit run log_query_ui.py
   ```

The UI enables easy exploration of logs with natural language inputs and helps visualize the underlying queries and results for effective log analysis.

### ⚙️ CI/CD Notes
- **Docker Scout** is commented out/disabled by default in the workflow because it requires a GitHub Pro/Team account or higher.
- To enable Docker Scout, adjust the repository settings: go to Actions → General → Workflow permissions, then set to Read/Write and allow create/approve PRs, or use a Personal Access Token (PAT) with appropriate permissions.
- **Release Please** requires the same `GITHUB_TOKEN` permissions to open PRs. Without these permissions, it will fail with the error "GitHub Actions is not permitted to create or approve pull requests".
- Snyk, Trivy, and Gitleaks artifacts are uploaded in the Actions run summary for download after each workflow run.

## Technologies Used

- Java 21+
- Spring Boot
- Spring Data JPA
- H2 Database
- Gradle
- Lombok (optional)

## Getting Started

```bash
./gradlew bootRun
```

Then navigate to `http://localhost:8080/api/employees`.

## H2 Console

- Visit: `http://localhost:8080/h2-console`
- JDBC URL: `jdbc:h2:mem:testdb`

## Project Structure

```
src
└── main
    └── java
        └── com.viplav.demo
            ├── controller
            ├── entity
            ├── service
            ├── repository
            ├── exception
            └── dto
```


## 🚀 Swagger UI

Once the application is running, visit:
```
http://localhost:8080/swagger-ui.html
```

## 📛 Badges

![Java CI](https://github.com/your-org/springboot-rest-api-template/actions/workflows/gradle.yml/badge.svg)
![Swagger](https://img.shields.io/badge/swagger-enabled-brightgreen)
![Docker](https://img.shields.io/badge/docker-ready-blue)


## ☸️ Kubernetes Deployment

```bash
kubectl apply -f k8s/deployment.yaml
```

## 🗂️ Architecture Overview

```text
Frontend (React / Postman / Swagger UI)
       |
       v
Spring Boot REST API (JWT Secured)
       |
       v
PostgreSQL (Flyway migrations)
       |
       v
Deployed via Docker Compose / Kubernetes / Helm
```

## 🚀 Deployment Guide

### Option 1: Run Locally
```bash
./gradlew bootRun
```

### Option 2: Docker Compose
```bash
docker-compose up --build
```

### Option 3: Kubernetes
```bash
kubectl apply -f k8s/deployment.yaml
```

### Option 4: Helm Chart
```bash
helm install employee-api ./helm/employee-api
```

### Swagger UI
Visit [http://localhost:8080/swagger-ui.html](http://localhost:8080/swagger-ui.html)


## 🔖 Releases (Conventional Commits → Auto Tags)
We use Conventional Commits and GitHub's **Release Please** to automate versioning and releases.
This project now includes integrated security scanning (Trivy, Docker Scout, Snyk, Gitleaks) and an AI-assisted STRIDE threat model review in CI/CD.

### How it works
- Push/merge commits to `main` using Conventional Commit prefixes (`feat:`, `fix:`, `perf:`, `refactor:`, `docs:`, etc.).
- The workflow opens/updates a **release PR** summarizing changes and proposing the next SemVer bump:
  - `fix:` → **patch**
  - `feat:` → **minor**
  - `BREAKING CHANGE:` (in body) → **major**
- When you **merge the release PR**, it automatically **creates a Git tag** `vX.Y.Z` and a GitHub release.
- Our CI builds the app and Docker image using that tag version and bakes it into `/actuator/info` and OCI labels.

### Commit examples
```
feat: add role-based filter to /users endpoint
fix: null pointer when JWT is missing
refactor(auth): simplify filter chain
```

### Manual fallback (optional)
If you need to cut a release without the PR flow:
```bash
VER=1.2.3
git tag -a "v${VER}" -m "Release v${VER}"
git push origin "v${VER}"
```
This also triggers CI with the exact `1.2.3` baked into the build.