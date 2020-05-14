update migration_version set version = 6;
alter table main_game add column created_on datetime not null;
update main_game set created_on = postinfo.start_post from ( select min("timestamp") as start_post, game_id from main_post group by game_id) AS postinfo WHERE postinfo.game_id = main_game.id ;