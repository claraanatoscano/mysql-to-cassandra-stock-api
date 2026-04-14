export PROJECT=p6
SERVER=${1:-server1}
echo "==> Rebuilding ${SERVER}..."
docker compose up --build -d -t 0 --no-deps ${SERVER}
echo "==> Running tests inside ${PROJECT}-${SERVER}-1..."
docker exec ${PROJECT}-${SERVER}-1 python3 -m pytest rest_test.py -v
