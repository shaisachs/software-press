FROM eclipse-temurin:17-jdk

ENV KARATE_VERSION=1.5.2 \
    POSTGRESQL_DRIVER_VERSION=42.7.4 \
    JEDIS_VERSION=5.1.0

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /karate/libs /karate/classes /karate/src

# Karate standalone JAR plus the jars needed by the feature files: the
# PostgreSQL JDBC driver (for row-level assertions via DbUtils) and Jedis with
# its dependencies (for direct Redis queue membership checks).
RUN curl -fSL -o /karate/karate.jar \
        "https://github.com/karatelabs/karate/releases/download/v${KARATE_VERSION}/karate-${KARATE_VERSION}.jar" \
    && curl -fSL -o /karate/libs/postgresql.jar \
        "https://repo1.maven.org/maven2/org/postgresql/postgresql/${POSTGRESQL_DRIVER_VERSION}/postgresql-${POSTGRESQL_DRIVER_VERSION}.jar" \
    && curl -fSL -o /karate/libs/jedis.jar \
        "https://repo1.maven.org/maven2/redis/clients/jedis/${JEDIS_VERSION}/jedis-${JEDIS_VERSION}.jar" \
    && curl -fSL -o /karate/libs/slf4j-api.jar \
        "https://repo1.maven.org/maven2/org/slf4j/slf4j-api/1.7.36/slf4j-api-1.7.36.jar" \
    && curl -fSL -o /karate/libs/commons-pool2.jar \
        "https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.12.0/commons-pool2-2.12.0.jar" \
    && curl -fSL -o /karate/libs/json.jar \
        "https://repo1.maven.org/maven2/org/json/json/20231013/json-20231013.jar" \
    && curl -fSL -o /karate/libs/gson.jar \
        "https://repo1.maven.org/maven2/com/google/code/gson/gson/2.10.1/gson-2.10.1.jar"

COPY DbUtils.java /karate/src/DbUtils.java

RUN javac -d /karate/classes /karate/src/DbUtils.java

WORKDIR /karate

ENTRYPOINT ["java", "-cp", "/karate/karate.jar:/karate/libs/*:/karate/classes", "com.intuit.karate.Main"]
