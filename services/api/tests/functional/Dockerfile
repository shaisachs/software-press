# Build stage: resolve all dependencies (karate-core, the PostgreSQL JDBC
# driver, Jedis) and compile the DbUtils helper via Gradle instead of
# downloading jars by hand.
FROM gradle:8.8-jdk17 AS build

WORKDIR /work

COPY settings.gradle build.gradle ./
COPY src ./src

RUN gradle --no-daemon installDist

# Runtime stage: the application plugin's installDist output bundles the
# runner jar plus every runtime dependency, so the image only needs a JRE.
FROM eclipse-temurin:17-jdk

COPY --from=build /work/build/install/karate-runner /opt/karate-runner

WORKDIR /tests

ENTRYPOINT ["/opt/karate-runner/bin/karate-runner"]
