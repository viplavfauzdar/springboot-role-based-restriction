# ---- build stage ----
FROM gradle:8.6-jdk21 AS builder
WORKDIR /src
COPY . .
RUN gradle clean bootJar --no-daemon

# ---- run stage ----
FROM gcr.io/distroless/java21-debian12:nonroot
ARG APP_VERSION=0.1.0-SNAPSHOT
WORKDIR /app
LABEL org.opencontainers.image.title="springboot-role-based-restriction" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.description="Spring Boot demo with role-based restriction" \
      org.opencontainers.image.source="https://github.com/viplavfauzdar/springboot-role-based-restriction" \
      org.opencontainers.image.vendor="viplavfauzdar" \
      org.opencontainers.image.licenses="Apache-2.0"
COPY --from=builder /src/build/libs/*.jar /app/app.jar
ENV APP_VERSION=${APP_VERSION}
USER nonroot
ENTRYPOINT ["java","-jar","/app/app.jar"]