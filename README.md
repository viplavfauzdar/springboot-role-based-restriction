# Spring Boot REST API Template

This is a basic REST API template built with Spring Boot, using an H2 in-memory database. It demonstrates typical structure, including layers for controller, service, repository, and entity.

## Technologies Used

- Java 17+
- Spring Boot
- Spring Data JPA
- H2 Database
- Maven
- Lombok (optional)

## Getting Started

```bash
./mvnw spring-boot:run
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
        └── com.example.demo
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