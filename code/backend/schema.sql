-- Run once as the RDS master user (see scripts/bootstrap-db.sh).
CREATE TABLE IF NOT EXISTS secrets (
  id         CHAR(32)         NOT NULL,
  ciphertext TEXT             NOT NULL,
  expires_at DATETIME         NOT NULL,
  views      INT UNSIGNED     NOT NULL DEFAULT 0,
  max_views  TINYINT UNSIGNED NOT NULL,
  PRIMARY KEY (id),
  KEY idx_secrets_expires (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
