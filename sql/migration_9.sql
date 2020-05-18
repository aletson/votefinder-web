UPDATE migration_version SET version = 9;
ALTER TABLE main_gameday CHANGE start_post start_post_id int;