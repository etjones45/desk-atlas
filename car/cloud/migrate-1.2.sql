-- One-time upgrade of an existing v1.1 database to v1.2. Run each line; "duplicate column" errors mean it's already done.
ALTER TABLE commands ADD COLUMN output TEXT;
ALTER TABLE clips ADD COLUMN files TEXT;
ALTER TABLE clips ADD COLUMN camera TEXT;
ALTER TABLE usage_daily ADD COLUMN energy_wh REAL;
ALTER TABLE usage_daily ADD COLUMN awake_s REAL;
ALTER TABLE usage_daily ADD COLUMN starlink_s REAL;
ALTER TABLE usage_daily ADD COLUMN good_s REAL;
CREATE TABLE IF NOT EXISTS outages (start REAL PRIMARY KEY, end REAL, cause TEXT);
CREATE TABLE IF NOT EXISTS speedtests (at REAL PRIMARY KEY, down REAL, up REAL, ping REAL, jitter REAL, network TEXT, profile TEXT, auto INTEGER, used_mb REAL, server TEXT);
CREATE TABLE IF NOT EXISTS drives (start REAL PRIMARY KEY, end REAL, checkins INTEGER, net TEXT);
ALTER TABLE clips ADD COLUMN encrypted INTEGER;
