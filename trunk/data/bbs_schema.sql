PRAGMA foreign_keys = ON;

CREATE TABLE accounts (
    id            INTEGER PRIMARY KEY,
	username      TEXT UNIQUE COLLATE NOCASE NOT NULL,
	firstname     TEXT NOT NULL,
	lastname      TEXT NOT NULL,
	passwd        TEXT NOT NULL,
	globals       INTEGER NOT NULL DEFAULT 1,
    ansi          INTEGER,
	active        INTEGER NOT NULL DEFAULT 0
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


CREATE TABLE user_perms (
    id            INTEGER PRIMARY KEY,
	account       INTEGER NOT NULL,
	access_group  INTEGER NOT NULL,
	FOREIGN KEY(account) REFERENCES accounts(id),
	FOREIGN KEY(access_group) REFERENCES access_groups(id)
);


INSERT INTO accounts (username, 
                      passwd, 
				      firstname, 
				      lastname, 
				      globals,
				      active) VALUES (
				      'sysop',
				      '08c484f85fa8e87031ecf419bd597da85eef96454e6db73fb691cd3945addfe7345e46b37343e2c7da7e12eab81c0f759360d3a06579afb7a2707dbd591526fb',
				      'Sonzo',
				      'Sysop',
				      1,
				      1
);
