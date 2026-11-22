#!/bin/bash
# Corre una sola vez, al crear el volumen, como superusuario del contenedor.
# Crea al owner (sin SUPERUSER ni CREATEROLE), los 4 roles de grupo y un usuario por grupo.
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username postgres --dbname "$POSTGRES_DB" \
  -v owner_pw="$NUKYRO_DB_OWNER_PASSWORD" \
  -v api_pw="$NUKYRO_DB_API_PASSWORD" -v admin_pw="$NUKYRO_DB_ADMIN_PASSWORD" \
  -v jobs_pw="$NUKYRO_DB_JOBS_PASSWORD" -v analytics_pw="$NUKYRO_DB_ANALYTICS_PASSWORD" \
  -v owner_user="$NUKYRO_DB_OWNER_USER" -v api_user="$NUKYRO_DB_API_USER" \
  -v admin_user="$NUKYRO_DB_ADMIN_USER" -v jobs_user="$NUKYRO_DB_JOBS_USER" \
  -v analytics_user="$NUKYRO_DB_ANALYTICS_USER" <<'SQL'
CREATE ROLE :"owner_user" LOGIN NOSUPERUSER NOCREATEROLE NOCREATEDB PASSWORD :'owner_pw';
ALTER DATABASE :"DBNAME" OWNER TO :"owner_user";

CREATE ROLE nukyro_api NOLOGIN;
CREATE ROLE nukyro_admin NOLOGIN;
CREATE ROLE nukyro_jobs NOLOGIN;
CREATE ROLE nukyro_analytics NOLOGIN;

CREATE ROLE :"api_user" LOGIN PASSWORD :'api_pw' IN ROLE nukyro_api;
CREATE ROLE :"admin_user" LOGIN PASSWORD :'admin_pw' IN ROLE nukyro_admin;
CREATE ROLE :"jobs_user" LOGIN PASSWORD :'jobs_pw' IN ROLE nukyro_jobs;
CREATE ROLE :"analytics_user" LOGIN PASSWORD :'analytics_pw' IN ROLE nukyro_analytics;

REVOKE CONNECT ON DATABASE :"DBNAME" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"DBNAME" TO :"api_user", :"admin_user", :"jobs_user", :"analytics_user";
SQL
