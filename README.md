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


## ☁️ AWS Deployment with Terraform + GitHub Actions

This project supports cloud deployment to AWS EC2 using a combination of Terraform for infrastructure provisioning and GitHub Actions for automated application deployment. Two main approaches are supported:

### 1. **Current Deployment (Manual + GHA Hybrid)**
- **Infrastructure**: Terraform scripts are used to provision an EC2 instance (e.g., `t4g.small` ARM64 for cost efficiency), security groups, and networking. The user runs `terraform apply` manually to create/update infrastructure.
- **Application Deployment**: The GitHub Actions workflow (`.github/workflows/deploy.yml`) builds the Docker image, pushes it to GitHub Container Registry (GHCR), and then SSHes into the EC2 instance to pull the latest image and restart the container.
- **Manual Steps**: Some manual intervention is required—primarily running `terraform apply` and updating secrets/SSH keys as needed.

### 2. **One-Click Automated Deployment**
- **Fully Automated**: By configuring Terraform to use a remote backend (S3 for state, DynamoDB for locking), both infrastructure and application deployment can be triggered from GitHub Actions with no manual steps.
- **Per-Environment Deployments**: Use environment variables or GitHub Environments (e.g., `dev`, `staging`, `prod`) to drive which environment is deployed. You can organize Terraform code using workspaces or separate folders (`infra/dev`, `infra/staging`, etc.), each with isolated state in S3.
- **Workflow**: On push or PR merge to a specific branch or environment, the workflow:
  - Runs `terraform init`, `terraform plan`, and `terraform apply` to provision/update infrastructure.
  - Builds and pushes the Docker image to GHCR.
  - SSHes into the EC2 instance, pulls the new image, and restarts the container.

#### Example GitHub Actions Workflow Snippet
```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ github.ref_name }}  # e.g., dev, staging, prod
    steps:
      - uses: actions/checkout@v4

      # Setup Terraform
      - uses: hashicorp/setup-terraform@v2
      - name: Terraform Init
        run: terraform init -backend-config="bucket=my-tf-state-${{ github.ref_name }}"
        working-directory: infra/${{ github.ref_name }}
      - name: Terraform Plan
        run: terraform plan
        working-directory: infra/${{ github.ref_name }}
      - name: Terraform Apply
        run: terraform apply -auto-approve
        working-directory: infra/${{ github.ref_name }}

      # Build & Push Docker Image to GHCR
      - name: Build Docker image
        run: docker build -t ghcr.io/${{ github.repository }}:${{ github.sha }} .
      - name: Login to GHCR
        run: echo ${{ secrets.GITHUB_TOKEN }} | docker login ghcr.io -u ${{ github.actor }} --password-stdin
      - name: Push Docker image
        run: docker push ghcr.io/${{ github.repository }}:${{ github.sha }}

      # SSH & Deploy on EC2
      - name: Deploy to EC2
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.EC2_HOST }}
          username: ec2-user
          key: ${{ secrets.EC2_SSH_KEY }}
          script: |
            docker pull ghcr.io/${{ github.repository }}:${{ github.sha }}
            docker stop springboot-app || true
            docker rm springboot-app || true
            docker run -d --name springboot-app -p 80:8080 ghcr.io/${{ github.repository }}:${{ github.sha }}
```

### 💸 Cost Optimization
- The Terraform scripts default to using ARM64-based EC2 instances (such as `t4g.small`) for significant cost savings while maintaining good performance. Be sure your Docker image is multi-arch or ARM64 compatible.

### 🔀 Multi-Environment Strategy
- **Workspaces**: Use Terraform workspaces (`terraform workspace select dev`) to isolate state per environment.
- **Per-Folder Structure**: Alternatively, maintain separate folders (e.g., `infra/dev`, `infra/staging`, `infra/prod`) with their own backend config.
- **State Storage**: Store Terraform state in S3 and use DynamoDB for state locking to avoid conflicts during concurrent deployments.


### 🌍 Environment Management Patterns

#### 1. **Directory-per-Environment Terraform**
Organize your Terraform code by creating a separate directory for each environment (e.g., `infra/dev`, `infra/staging`, `infra/prod`). Each folder contains its own Terraform files and state, making it easy to manage and isolate changes.

Example structure:
```text
infra/
├── dev/
│   ├── main.tf
│   ├── variables.tf
│   └── backend.tf
├── staging/
│   ├── main.tf
│   ├── variables.tf
│   └── backend.tf
└── prod/
    ├── main.tf
    ├── variables.tf
    └── backend.tf
```

#### 2. **Workspace-per-Environment Terraform**
Alternatively, use [Terraform workspaces](https://developer.hashicorp.com/terraform/language/state/workspaces) to isolate state for each environment within the same codebase. This is useful when the infrastructure is similar across environments.

Example commands:
```sh
# List all workspaces
terraform workspace list
# Create/select a workspace
terraform workspace new dev
terraform workspace select staging
# Apply changes to the selected workspace
terraform apply
```

#### 3. **Remote State Backend (S3 + DynamoDB)**
Store Terraform state in an S3 bucket and use DynamoDB for state locking to prevent concurrent modifications. This is critical for team workflows and GitHub Actions automation.

Example `backend.tf` snippet:
```hcl
terraform {
  backend "s3" {
    bucket         = "my-tf-state-dev"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "my-tf-locks"
    encrypt        = true
  }
}
```

#### 4. **GitHub Environments Integration**
Map GitHub Environments (e.g., dev, staging, prod) to your Terraform directories or workspaces. This enables environment-specific approvals and secrets in GitHub Actions.

Example GitHub Actions workflow snippet:
```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ github.ref_name }}  # Maps to dev, staging, prod
    steps:
      # ...
      - name: Terraform Init
        run: terraform init -backend-config="bucket=my-tf-state-${{ github.ref_name }}"
        working-directory: infra/${{ github.ref_name }}
      # ...
```

#### 5. **Secrets Management**
Use GitHub Secrets to securely inject sensitive values (like EC2_HOST, EC2_SSH_KEY, AWS credentials) into your workflows. Reference them in your workflow as environment variables or inputs.

Example usage in GitHub Actions:
```yaml
      - name: Deploy to EC2
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.EC2_HOST }}
          username: ec2-user
          key: ${{ secrets.EC2_SSH_KEY }}
          envs: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
```

#### 6. **Minimal Variables per Environment**
Define environment-specific variables in separate tfvars files (e.g., `dev.tfvars`, `staging.tfvars`). Pass the appropriate file when running Terraform.

Example `dev.tfvars`:
```hcl
instance_type = "t4g.small"
env_name      = "dev"
```

Apply with:
```sh
terraform apply -var-file=dev.tfvars
```