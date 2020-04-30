UPDATE migration_version SET version = 5;
alter table main_gameday add column `state` varchar(32) after `name`;
update main_gameday set state = 'closed' where closed = 1;
update main_gameday set state = 'started' where closed = 0;
alter table main_game drop column `closed`;