#!/usr/bin/with-contenv bashio

while true; do
  python /app/check_stock.py
  sleep "$(bashio::config 'interval_seconds')"
done
