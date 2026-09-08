#!/bin/sh
# Runs once, on first initialization of an empty pgdata volume.
# Creates the test database alongside the dev database ($POSTGRES_DB).
set -e

createdb --username "$POSTGRES_USER" --owner "$POSTGRES_USER" "${POSTGRES_DB}_test"
