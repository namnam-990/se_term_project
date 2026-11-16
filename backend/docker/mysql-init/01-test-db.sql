-- 통합 테스트 전용 DB (tests/integration 이 테이블을 지우고 다시 만듦)
-- MySQL 볼륨이 처음 만들어질 때만 실행됨. 이미 볼륨이 있으면: docker compose down -v 후 다시 up
CREATE DATABASE IF NOT EXISTS lsrs_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON lsrs_test.* TO 'lsrs'@'%';
FLUSH PRIVILEGES;
