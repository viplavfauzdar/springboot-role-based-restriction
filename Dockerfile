# ---- build stage ----
FROM gradle:8.6-jdk21 AS builder
WORKDIR /src
COPY . .
RUN gradle clean bootJar --no-daemon

# ---- run stage ----
FROM gcr.io/distroless/java21-debian12:nonroot
WORKDIR /app
COPY --from=builder /src/build/libs/*-SNAPSHOT.jar /app/app.jar
USER nonroot
ENTRYPOINT ["java","-jar","/app/app.jar"]