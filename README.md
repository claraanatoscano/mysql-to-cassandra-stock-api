# MySQL to Cassandra Stock API

A Flask REST API for stock prices, ported from MySQL to Apache Cassandra. The project translates a relational design (primary and foreign keys, JOINs, GROUP BY) into Cassandra's distributed data model, and tunes replication and quorum settings so reads stay available even when a database node fails. The full system runs locally in Docker.

Built for CS 544: Introduction to Big Data Systems at UW–Madison (Spring 2026).

## How it works

```
client → server1 (Flask) → MySQL                   (original version, provided)
client → server2 (Flask) → Cassandra, 3 nodes      (my port)
```

- **server1:** the original stock price API backed by MySQL, provided as the starting point.
- **server2:** my Cassandra version of the same API, built with the Python `cassandra-driver`.
- **Tests:** pytest integration tests that send real requests to the running Flask servers.

## Key design work

- **Schema translation:** replaced foreign keys and JOINs with a single Cassandra table, using partition keys, clustering keys, and static columns to store related data together.
- **Client-side aggregation:** Cassandra doesn't support SQL-style GROUP BY, so aggregations are computed in Python.
- **Fault tolerance:** chose the replication factor and read/write quorum settings (R and W) so reads keep working when one of the three Cassandra nodes goes down.
- **AI-assisted development:** used Aider with Gemini 2.5 Pro for parts of the implementation, as the course required.

## Tech stack

Python · Flask · Apache Cassandra · MySQL · pytest · Docker Compose · Aider (Gemini 2.5 Pro)

## Project structure

```
server1.py           Flask API backed by MySQL (provided)
server2.py           Flask API backed by Cassandra (my port)
rest_test.py         pytest integration tests
mysql/, cassandra/   Database images and setup
docker-compose.yml   MySQL, a 3-node Cassandra cluster, and both servers
port.sh              Helper for finding the servers' mapped ports
```

## Running it

Requires Docker and Docker Compose.

```bash
export PROJECT=p6
docker compose up --build -d -t 0
```
