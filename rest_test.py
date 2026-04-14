import requests
import pytest

BASE = "http://localhost:5000"
DB   = "test"

def url(*parts):
    return "/".join([BASE, DB, "api"] + list(parts))

def test_create_company():
    r = requests.post(url("companies", "TSLA"), json={"name": "Tesla Inc.", "sector": "Automotive"})
    assert r.status_code == 201
    body = r.json()
    assert body["ticker"] == "TSLA"
    assert body["name"]   == "Tesla Inc."
    assert body["sector"] == "Automotive"

def test_create_company_upsert():
    requests.post(url("companies", "UPSERTCO"), json={"name": "Old Name", "sector": "Old Sector"})
    r = requests.post(url("companies", "UPSERTCO"), json={"name": "New Name", "sector": "New Sector"})
    assert r.status_code == 201
    assert r.json()["name"] == "New Name"

def test_create_company_missing_fields():
    r = requests.post(url("companies", "BADINPUT"), json={"name": "Only Name"})
    assert r.status_code == 400

def test_get_company():
    requests.post(url("companies", "AAPL"), json={"name": "Apple Inc.", "sector": "Technology"})
    r = requests.get(url("companies", "AAPL"))
    assert r.status_code == 200
    body = r.json()
    assert body["ticker"] == "AAPL"
    assert body["name"]   == "Apple Inc."
    assert body["sector"] == "Technology"

def test_get_company_not_found():
    r = requests.get(url("companies", "ZZZZNOTREAL"))
    assert r.status_code == 404

def test_upsert_record_two_dates():
    requests.post(url("companies", "MSFT"), json={"name": "Microsoft", "sector": "Technology"})
    r1 = requests.post(url("companies", "MSFT", "records", "2024-01-02"), json={"high": 380.0, "low": 370.0})
    assert r1.status_code == 201
    assert r1.json()["high"] == 380.0
    assert r1.json()["low"]  == 370.0
    assert r1.json()["date"] == "2024-01-02"
    r2 = requests.post(url("companies", "MSFT", "records", "2024-01-03"), json={"high": 390.0, "low": 375.0})
    assert r2.status_code == 201
    assert r2.json()["high"] == 390.0
    assert r2.json()["date"] == "2024-01-03"

def test_upsert_record_same_date_overwrites():
    requests.post(url("companies", "GOOG"), json={"name": "Alphabet", "sector": "Technology"})
    requests.post(url("companies", "GOOG", "records", "2024-03-01"), json={"high": 150.0, "low": 140.0})
    requests.post(url("companies", "GOOG", "records", "2024-03-01"), json={"high": 999.0, "low": 888.0})
    check = requests.get(url("companies", "GOOG", "records", "2024-03-01"))
    assert check.status_code == 200
    assert check.json()["high"] == 999.0
    assert check.json()["low"]  == 888.0

def test_upsert_record_missing_fields():
    requests.post(url("companies", "BADREC"), json={"name": "Bad Co", "sector": "Misc"})
    r = requests.post(url("companies", "BADREC", "records", "2024-01-01"), json={"high": 100.0})
    assert r.status_code == 400

def test_get_records_multiple():
    requests.post(url("companies", "NFLX"), json={"name": "Netflix", "sector": "Entertainment"})
    dates = ["2024-02-01", "2024-02-02", "2024-02-03"]
    for i, d in enumerate(dates):
        requests.post(url("companies", "NFLX", "records", d), json={"high": 500.0 + i, "low": 490.0 + i})
    r = requests.get(url("companies", "NFLX", "records"))
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 3
    assert [row["date"] for row in rows] == sorted([row["date"] for row in rows])
    assert rows[0]["high"] == 500.0
    assert rows[2]["high"] == 502.0

def test_get_records_empty_company():
    requests.post(url("companies", "EMPTY1"), json={"name": "Empty Corp", "sector": "Nothing"})
    r = requests.get(url("companies", "EMPTY1", "records"))
    assert r.status_code == 200
    assert r.json() == []

def test_get_single_record():
    requests.post(url("companies", "AMZN"), json={"name": "Amazon", "sector": "E-Commerce"})
    requests.post(url("companies", "AMZN", "records", "2024-04-10"), json={"high": 185.0, "low": 180.0})
    r = requests.get(url("companies", "AMZN", "records", "2024-04-10"))
    assert r.status_code == 200
    body = r.json()
    assert body["ticker"] == "AMZN"
    assert body["date"]   == "2024-04-10"
    assert body["high"]   == 185.0
    assert body["low"]    == 180.0

def test_get_single_record_not_found():
    requests.post(url("companies", "META"), json={"name": "Meta", "sector": "Social Media"})
    r = requests.get(url("companies", "META", "records", "1900-01-01"))
    assert r.status_code == 404

def test_get_monthly_averages():
    requests.post(url("companies", "AVGCO"), json={"name": "Average Co", "sector": "Finance"})
    requests.post(url("companies", "AVGCO", "records", "2024-01-10"), json={"high": 100.0, "low": 90.0})
    requests.post(url("companies", "AVGCO", "records", "2024-01-20"), json={"high": 200.0, "low": 180.0})
    requests.post(url("companies", "AVGCO", "records", "2024-02-05"), json={"high": 300.0, "low": 280.0})
    r = requests.get(url("companies", "AVGCO", "records", "monthly"))
    assert r.status_code == 200
    months = r.json()
    assert len(months) == 2
    assert months[0]["month"]    == "2024-01"
    assert months[0]["avg_high"] == pytest.approx(150.0)
    assert months[0]["avg_low"]  == pytest.approx(135.0)
    assert months[1]["month"]    == "2024-02"
    assert months[1]["avg_high"] == pytest.approx(300.0)
    assert months[1]["avg_low"]  == pytest.approx(280.0)

def test_get_monthly_order():
    requests.post(url("companies", "ORDCO"), json={"name": "Order Co", "sector": "Logistics"})
    for month in ["2024-03", "2024-01", "2024-02"]:
        requests.post(url("companies", "ORDCO", "records", f"{month}-15"), json={"high": 50.0, "low": 45.0})
    r = requests.get(url("companies", "ORDCO", "records", "monthly"))
    months = [m["month"] for m in r.json()]
    assert months == sorted(months)
