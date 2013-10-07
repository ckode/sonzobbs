PRAGMA foreign_keys = ON;

CREATE TABLE accounts (
    id            INTEGER PRIMARY KEY,
	username      TEXT NOT NULL,
	firstname     TEXT NOT NULL,
	lastname      TEXT NOT NULL,
	passwd        TEXT NOT NULL,
	globals       INTEGER NOT NULL DEFAULT 1,
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
				      'd57b9857a088cd23154d3ba0461cdac61adc738fdc12b68f243977b8',
				      'Sonzo',
				      'Sysop',
				      1,
				      1
);
	