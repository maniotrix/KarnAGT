import os
import psycopg2
import redis
import requests
from neo4j import GraphDatabase
from urllib.parse import urlparse


def check_postgres():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB", "chatgpt_clone"),
            user=os.getenv("POSTGRES_USER", "chatgpt_user"),
            password=os.getenv("POSTGRES_PASSWORD", "chatgpt_password"),
            host="localhost",
            port=5432
        )
        conn.close()
        print("✅ Postgres is reachable")
    except Exception as e:
        print(f"❌ Postgres failed: {e}")


def check_redis():
    try:
        r = redis.Redis(host="localhost", port=6379, db=0)
        r.ping()
        print("✅ Redis is reachable")
    except Exception as e:
        print(f"❌ Redis failed: {e}")


def check_qdrant():
    try:
        res = requests.get("http://localhost:6333/collections")
        if res.status_code == 200:
            print("✅ Qdrant is reachable")
        else:
            print(f"❌ Qdrant error: HTTP {res.status_code}")
    except Exception as e:
        print(f"❌ Qdrant failed: {e}")


def check_neo4j():
    try:
        uri = "bolt://localhost:7687"
        user = os.getenv("NEO4J_USERNAME", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "neo4j_password")
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            result = session.run("RETURN 1")
            if result.single()[0] == 1:
                print("✅ Neo4j is reachable")
            else:
                print("❌ Neo4j query failed")
        driver.close()
    except Exception as e:
        print(f"❌ Neo4j failed: {e}")


if __name__ == "__main__":
    check_postgres()
    check_redis()
    check_qdrant()
    check_neo4j()
