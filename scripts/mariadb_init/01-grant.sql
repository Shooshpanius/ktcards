-- Ensures the application user has all privileges on the ktcards database.
-- This script is executed by the MariaDB container only on first-time
-- initialization (i.e. when the data directory is empty).
-- It supplements the automatic MYSQL_USER grant to make permissions explicit
-- and to guard against scenarios where the automatic grant is skipped.

GRANT ALL PRIVILEGES ON `ktcards`.* TO `ktcards`@`%`;
FLUSH PRIVILEGES;
