-- Run as database administrator after creating private, separately authenticated
-- accounts sympress_web and sympress_migrate. Replace database and host names.
-- Existing accounts must be reviewed/revoked before applying these additive grants.
GRANT SELECT, INSERT, UPDATE, DELETE ON `sympress`.* TO 'sympress_web'@'php';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, DROP,
      CREATE TEMPORARY TABLES, LOCK TABLES
    ON `sympress`.* TO 'sympress_migrate'@'migration';
-- Neither account gets global privileges, FILE, GRANT OPTION or user administration.
