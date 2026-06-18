-- --------------------------------------------------------
-- 1. 确保数据库存在并切换环境
-- --------------------------------------------------------
CREATE DATABASE IF NOT EXISTS res_queue_db DEFAULT CHARSET utf8mb4;
USE res_queue_db;

-- --------------------------------------------------------
-- 2. 彻底清理旧表结构（防止因表已存在导致字段无法更新）
-- --------------------------------------------------------
DROP TABLE IF EXISTS queue_record;
DROP TABLE IF EXISTS kucun;

-- --------------------------------------------------------
-- 3. 重新创建：完整的排队记录表（包含缺失的 status 字段）
-- --------------------------------------------------------
CREATE TABLE queue_record (
    id INT PRIMARY KEY AUTO_INCREMENT,
    queue_number VARCHAR(20) NOT NULL,
    queue_type VARCHAR(20) NOT NULL,       -- 'normal' 或 'VIP'
    people_count INT NOT NULL,
    status VARCHAR(20) DEFAULT 'waiting',  -- 'waiting'(排队), 'called'(就餐), 'missed'(过号)
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- --------------------------------------------------------
-- 4. 重新创建：食材库存表
-- --------------------------------------------------------
CREATE TABLE kucun (
    id INT PRIMARY KEY AUTO_INCREMENT,
    food_name VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'normal',   -- 'normal'(正常), 'expired'(过期)
    expire_date DATE DEFAULT NULL          -- 日期标签
);

-- --------------------------------------------------------
-- 5. 初始化：写入后厨看板的基础食材数据
-- --------------------------------------------------------
INSERT INTO kucun (food_name, status) VALUES
('牛肉', 'normal'),
('鸡蛋', 'normal'),
('生菜', 'normal'),
('土豆', 'normal'),
('虾仁', 'normal'),
('鸡胸肉', 'normal');

-- --------------------------------------------------------
-- 6. 权限与用户安全配置
-- --------------------------------------------------------
CREATE USER IF NOT EXISTS 'ResQueue'@'localhost' IDENTIFIED BY '123456';
ALTER USER 'ResQueue'@'localhost' IDENTIFIED WITH mysql_native_password BY '123456';
GRANT ALL PRIVILEGES ON res_queue_db.* TO 'ResQueue'@'localhost';
FLUSH PRIVILEGES;