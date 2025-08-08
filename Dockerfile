FROM openjdk:21-jdk-slim
VOLUME /tmp
COPY build/libs/*-SNAPSHOT.jar /app.jar
ENTRYPOINT ["java","-jar","/app.jar"]