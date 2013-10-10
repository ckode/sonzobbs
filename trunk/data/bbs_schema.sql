PRAGMA foreign_keys = ON;

CREATE TABLE accounts (
    id            INTEGER PRIMARY KEY,
	username      TEXT UNIQUE COLLATE NOCASE NOT NULL,
	firstname     TEXT NOT NULL,
	lastname      TEXT NOT NULL,
	passwd        TEXT NOT NULL,
    email         TEXT NOT NULL,
	globals       INTEGER NOT NULL DEFAULT 1,
    ansi          INTEGER,
	active        INTEGER NOT NULL DEFAULT 0,
    sec_code      INTEGER NOT NULL DEFAULT (ABS(RANDOM() % 100000000))
);

CREATE TABLE bbsroles (
    id            INTEGER PRIMARY KEY,
	name          TEXT NOT NULL,
	bbsrole       INTEGER NOT NULL
);

CREATE TABLE access_groups (
    id            INTEGER PRIMARY KEY,
	name          TEXT NOT NULL,
	account       INTEGER NOT NULL,
	FOREIGN KEY(account) REFERENCES accounts(id)
);

CREATE TABLE group_perms (
    id            INTEGER PRIMARY KEY,
	access_group  INTEGER NOT NULL,
	bbsrole       INTEGER NOT NULL,
	FOREIGN KEY(access_group) REFERENCES access_groups(id),
	FOREIGN KEY(bbsrole) REFERENCES bbsroles(id)
);


CREATE TABLE account_perms (
    id            INTEGER PRIMARY KEY,
	account       INTEGER NOT NULL,
	access_group  INTEGER NOT NULL,
	FOREIGN KEY(account) REFERENCES accounts(id),
	FOREIGN KEY(access_group) REFERENCES access_groups(id)
);

CREATE TABLE account_notes (
    id            INTEGER PRIMARY KEY,
    account       INTEGER NOT NULL,
    note          TEXT NOT NULL,
    note_date     DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(account) REFERENCES accounts(id)
);

INSERT INTO accounts (username, 
                      passwd, 
				      firstname, 
				      lastname, 
                      email,
				      globals,
				      active) VALUES (
				      'sysop',
				      '08c484f85fa8e87031ecf419bd597da85eef96454e6db73fb691cd3945addfe7345e46b37343e2c7da7e12eab81c0f759360d3a06579afb7a2707dbd591526fb',
				      'Sonzo',
				      'Sysop',
                      'here@there.com',
				      1,
				      1
);

INSERT INTO account_notes (account, note) VALUES (1, "Test note");