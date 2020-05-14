update migration_version set version = 6;
alter table main_game add column created_on datetime not null;
UPDATE main_game JOIN (SELECT MIN(`timestamp`) AS start_post, game_id FROM main_post GROUP BY game_id) postinfo SET created_on = postinfo.start_post WHERE postinfo.game_id = main_game.id;