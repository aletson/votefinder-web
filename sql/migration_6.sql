update migration_version set version = 6;
alter table main_game add column created_on timestamp with time zone;
update main_game set created_on = postinfo.start_post from ( select min("timestamp") as start_post, game_id from main_post group by game_id) AS postinfo WHERE postinfo.game_id = main_game.id
update main_game set "lastUpdated" = postinfo.end_post from ( select max("timestamp") as end_post, game_id from main_post group by game_id) AS postinfo WHERE postinfo.game_id = main_game.id