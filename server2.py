import time
import collections
import os
from flask import Flask, request, jsonify
from cassandra.cluster import Cluster
from cassandra.policies import RoundRobinPolicy
from cassandra import ConsistencyLevel

app = Flask(__name__)

CASSANDRA_HOST = os.environ.get("CASSANDRA_HOST", "cassandra")


def wait_for_cassandra():
    for _ in range(60):
        try:
            cluster = Cluster([CASSANDRA_HOST], load_balancing_policy=RoundRobinPolicy(), connect_timeout=30, control_connection_timeout=30)
            session = cluster.connect()
            session.shutdown()
            cluster.shutdown()
            return
        except Exception as e:
            print(f"Waiting for Cassandra: {e}")
            time.sleep(5)
    raise RuntimeError("Could not connect to Cassandra after retries")


def init_cassandra():
    cluster = Cluster([CASSANDRA_HOST], load_balancing_policy=RoundRobinPolicy(), connect_timeout=30, control_connection_timeout=30)
    session = cluster.connect()
    session.default_timeout = 60
    for ks in ("prod", "test"):
        session.execute(f"""
            CREATE KEYSPACE IF NOT EXISTS {ks}
            WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 3}}
        """)
        session.execute(f"""
            CREATE TABLE IF NOT EXISTS {ks}.stocks (
                ticker  TEXT,
                date    DATE,
                name    TEXT STATIC,
                sector  TEXT STATIC,
                high    DOUBLE,
                low     DOUBLE,
                PRIMARY KEY (ticker, date)
            ) WITH CLUSTERING ORDER BY (date ASC)
        """)
    session.default_consistency_level = ConsistencyLevel.QUORUM
    return session


wait_for_cassandra()
SESSION = init_cassandra()


@app.route("/<db>/api/companies/<ticker>", methods=["POST"])
def add_company(db, ticker):
    data = request.get_json()
    name = data.get("name")
    sector = data.get("sector")
    if not all([name, sector]):
        return jsonify({"error": "name and sector are required"}), 400
    SESSION.execute(
        f"INSERT INTO {db}.stocks (ticker, name, sector) VALUES (%s, %s, %s)",
        (ticker, name, sector)
    )
    return jsonify({"ticker": ticker, "name": name, "sector": sector}), 201


@app.route("/<db>/api/companies/<ticker>", methods=["GET"])
def get_company(db, ticker):
    rows = list(SESSION.execute(
        f"SELECT ticker, name, sector FROM {db}.stocks WHERE ticker = %s",
        (ticker,)
    ))
    if not rows or rows[0].name is None:
        return jsonify({"error": "not found"}), 404
    row = rows[0]
    return jsonify({"ticker": row.ticker, "name": row.name, "sector": row.sector})


@app.route("/<db>/api/companies/<ticker>/records/<date>", methods=["POST"])
def add_stock(db, ticker, date):
    data = request.get_json()
    high = data.get("high")
    low = data.get("low")
    if any(v is None for v in [high, low]):
        return jsonify({"error": "high and low are required"}), 400
    company = list(SESSION.execute(
        f"SELECT name FROM {db}.stocks WHERE ticker = %s",
        (ticker,)
    ))
    if not company or company[0].name is None:
        return jsonify({"error": "company not found"}), 404
    SESSION.execute(
        f"INSERT INTO {db}.stocks (ticker, date, high, low) VALUES (%s, %s, %s, %s)",
        (ticker, date, high, low)
    )
    return jsonify({"ticker": ticker, "date": date, "high": high, "low": low}), 201


@app.route("/<db>/api/companies/<ticker>/records", methods=["GET"])
def get_stocks(db, ticker):
    rows = list(SESSION.execute(
        f"SELECT ticker, date, high, low FROM {db}.stocks WHERE ticker = %s",
        (ticker,)
    ))
    result = []
    for row in rows:
        if row.date is None:
            continue
        result.append({
            "ticker": row.ticker,
            "date": str(row.date),
            "high": row.high,
            "low": row.low,
        })
    return jsonify(result)


@app.route("/<db>/api/companies/<ticker>/records/<date>", methods=["GET"])
def get_stock_date(db, ticker, date):
    rows = list(SESSION.execute(
        f"SELECT ticker, date, high, low FROM {db}.stocks WHERE ticker = %s AND date = %s",
        (ticker, date)
    ))
    if not rows or rows[0].date is None:
        return jsonify({"error": "not found"}), 404
    row = rows[0]
    return jsonify({"ticker": row.ticker, "date": str(row.date), "high": row.high, "low": row.low})


@app.route("/<db>/api/companies/<ticker>/records/monthly", methods=["GET"])
def get_stock_monthly(db, ticker):
    rows = list(SESSION.execute(
        f"SELECT date, high, low FROM {db}.stocks WHERE ticker = %s",
        (ticker,)
    ))
    buckets = collections.defaultdict(lambda: {"highs": [], "lows": []})
    for row in rows:
        if row.date is None:
            continue
        month = str(row.date)[:7]
        buckets[month]["highs"].append(row.high)
        buckets[month]["lows"].append(row.low)
    result = []
    for month in sorted(buckets.keys()):
        highs = buckets[month]["highs"]
        lows = buckets[month]["lows"]
        result.append({
            "month": month,
            "avg_high": round(sum(highs) / len(highs), 4),
            "avg_low": round(sum(lows) / len(lows), 4),
        })
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
