SET SESSION storage_engine = "InnoDB";
SET SESSION time_zone = "+0:00";
ALTER DATABASE CHARACTER SET "utf8";


CREATE TABLE IF NOT EXISTS access (
    access VARBINARY(32) NOT NULL PRIMARY KEY,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS timebank (
    fingerprint VARBINARY(32) NOT NULL,
    currency VARBINARY(32) NOT NULL,
    balance DOUBLE NOT NULL DEFAULT 0,
    PRIMARY KEY(fingerprint,currency),
    KEY(currency)
);
CREATE TABLE IF NOT EXISTS timebank_quota (
    currency VARBINARY(32) NOT NULL PRIMARY KEY,
    universal BIT NOT NULL DEFAULT 1,
    duplicity DOUBLE NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS speech (
    dchash VARBINARY(32) NOT NULL PRIMARY KEY,
    source VARBINARY(32) NOT NULL,
    target VARBINARY(32) DEFAULT NULL,
    intent VARBINARY(32) NOT NULL,
    voice DOUBLE NOT NULL DEFAULT 1,
    active BIT NOT NULL DEFAULT 1,
    content TEXT NOT NULL,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    KEY(source,active),
    KEY(target,active),
    KEY(intent,active)
);
