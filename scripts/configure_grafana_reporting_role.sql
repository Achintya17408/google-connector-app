\set ON_ERROR_STOP on

SELECT format('CREATE ROLE grafana_reader LOGIN PASSWORD %L', :'reader_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'grafana_reader') \gexec

SELECT format('ALTER ROLE grafana_reader PASSWORD %L', :'reader_password') \gexec
ALTER ROLE grafana_reader SET default_transaction_read_only = on;
ALTER ROLE grafana_reader SET statement_timeout = '30s';
ALTER ROLE grafana_reader SET idle_in_transaction_session_timeout = '60s';
ALTER ROLE grafana_reader CONNECTION LIMIT 3;

SELECT format('GRANT CONNECT ON DATABASE %I TO grafana_reader', current_database()) \gexec
GRANT USAGE ON SCHEMA reporting TO grafana_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA reporting TO grafana_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA reporting
  GRANT SELECT ON TABLES TO grafana_reader;

REVOKE ALL ON TABLE google_oauth_credentials FROM grafana_reader;
REVOKE ALL ON SCHEMA public FROM grafana_reader;
GRANT USAGE ON SCHEMA public TO grafana_reader;

SELECT current_database() AS database,
       rolname,
       rolconnlimit,
       rolcanlogin
FROM pg_roles
WHERE rolname = 'grafana_reader';
