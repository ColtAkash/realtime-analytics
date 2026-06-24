FROM eclipse-temurin:17-jdk-jammy

RUN apt-get update && \
    apt-get install -y --no-install-recommends python3 python3-pip python3-venv curl && \
    rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir pyspark==3.5.6

WORKDIR /app

# Download connector JARs
RUN mkdir -p /app/jars && \
    curl -sL -o /app/jars/spark-sql-kafka.jar \
      "https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.5.6/spark-sql-kafka-0-10_2.12-3.5.6.jar" && \
    curl -sL -o /app/jars/kafka-clients.jar \
      "https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.7.0/kafka-clients-3.7.0.jar" && \
    curl -sL -o /app/jars/spark-token-provider.jar \
      "https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.5.6/spark-token-provider-kafka-0-10_2.12-3.5.6.jar" && \
    curl -sL -o /app/jars/commons-pool2.jar \
      "https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.12.0/commons-pool2-2.12.0.jar" && \
    curl -sL -o /app/jars/spark-cassandra-connector-assembly.jar \
      "https://repo1.maven.org/maven2/com/datastax/spark/spark-cassandra-connector-assembly_2.12/3.5.1/spark-cassandra-connector-assembly_2.12-3.5.1.jar" && \
    curl -sL -o /app/jars/elasticsearch-spark.jar \
      "https://repo1.maven.org/maven2/org/elasticsearch/elasticsearch-spark-30_2.12/8.13.0/elasticsearch-spark-30_2.12-8.13.0.jar"

COPY transforms.py aggregator.py ./

ENV PYSPARK_SUBMIT_ARGS="--jars /app/jars/spark-sql-kafka.jar,/app/jars/kafka-clients.jar,/app/jars/spark-token-provider.jar,/app/jars/commons-pool2.jar,/app/jars/spark-cassandra-connector-assembly.jar,/app/jars/elasticsearch-spark.jar pyspark-shell"

CMD ["python", "/app/aggregator.py"]
