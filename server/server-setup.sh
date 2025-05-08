#!/usr/bin/env bash
for p in 80 1883; do
  echo "Checking that port $p is free"
  if ss -tln '( sport = :'"$p"' )' | grep -q ":$p "; then
    echo "Port $p is already in use, ports 80,1883 must be free to continue"
    exit 1
  fi
done

echo "Checking for Docker"
if ! command -v docker &>/dev/null; then
  echo "Docker not found – downloading"
  curl -fsSL https://get.docker.com | sudo sh
else
  echo "Docker already installed"
fi

echo "Cloning cardiotron repository"
git clone https://github.com/ktnlvr/cardiotron.git

echo "Starting server containers"
cd cardiotron/server || exit 1
docker compose -f compose.yaml up -d

echo "Server containers are up"
