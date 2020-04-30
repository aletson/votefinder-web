UPDATE migration_version SET version = 5;
alter table main_game add column `state` varchar(32) after `name`;
update main_game set state = 'closed' where closed = 1;
update main_game set state = 'started' where closed = 0;
alter table main_game drop column `closed`;