create database if not exists clubot;
use clubot;

-- 创建成员数据库 members
-- key       type         default
-- id     INTEGER PRIMARY KEY AUTO_INCREMENT  null
-- email  VARCHAR          null
-- name   VARCHAR          null
-- nick   VARCHAR          null
-- last   timestamp         // 最后发言
-- lastchange timestamp     // 最后修改
-- isonline   INT           // 是否在线(0否, 1 是)
-- date timestamp           // 加入时间

create table if not exists members(
    id INT NOT NULL AUTO_INCREMENT,
    email VARCHAR(100) NOT NULL,
    name  VARCHAR(100) NOT NULL,
    nick VARCHAR(50) NOT NULL,
    last TIMESTAMP NOT NULL,
    lastchange TIMESTAMP NOT NULL,
    isonline INT NOT NULL DEFAULT 1,
    date TIMESTAMP NOT NULL,
    PRIMARY KEY(`id`),
    index(email),
    index(nick)
)character set utf8;

-- 创建信息数据库 info
create table if not exists info(
    id INT NOT NULL AUTO_INCREMENT,
    email VARCHAR(100) NOT NULL DEFAULT "global",
    `key` VARCHAR(255) NOT NULL,
    value TEXT NOT NULL,
    createdate TIMESTAMP NOT NULL,
    PRIMARY KEY(id),
    index(`key`),
    index(email)
    )character set utf8;


-- 创建聊天记录表 history
-- key              type              default
-- id         INTEGER PRIMARY KEY AUTO_INCREMNT null
-- frmemail        VARCHAR       null
-- content    TEXT          null
-- toemail     VARCHAR       null             // all代表所有,其余对应相应的email
-- date       TIMESTAMP     (datetime('now', 'localtime'))

create table if not exists history(
    id INT NOT NULL AUTO_INCREMENT,
    frmemail VARCHAR(100) NOT NULL,
    toemail VARCHAR(100) NOT NULL DEFAULT "all",
    content TEXT NOT NULL,
    date TIMESTAMP NOT NULL,
    PRIMARY KEY (id),
    index(frmemail),
    index(toemail)
)character set utf8;



-- 状态表 status
-- `key`               `type`              `default`
-- email      VARCHAR                       null
-- resource   VARCHAR                      null
-- status     INTEGER                       1 // 1在线,0不在线
-- statustext VARCHAR                      null

create table if not exists status(
    id INT NOT NULL AUTO_INCREMENT,
    email VARCHAR(100) NOT NULL,
    resource VARCHAR(100) NOT NULL,
    status INTEGER NOT NULL DEFAULT 1,
    statustext VARCHAR(100) NULL,
    PRIMARY KEY(id),
    index(email)
)character set utf8;
