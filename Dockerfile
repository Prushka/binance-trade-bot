FROM --platform=$BUILDPLATFORM python:3.12.2 as builder

WORKDIR /install

RUN apt-get update && apt-get install -y rustc

COPY requirements.txt /requirements.txt
RUN pip install --prefix=/install -r /requirements.txt

FROM python:3.12.2-slim

WORKDIR /app

COPY --from=builder /install /usr/local
COPY . .

CMD ["python", "-m", "binance_trade_bot"]
