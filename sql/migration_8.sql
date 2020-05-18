update migration_version set version = 8;
RENAME TABLE main_lynchmessage TO main_executionmessage;
UPDATE main_executionmessage SET `text` = REPLACE(`text`, '%s', '{}');