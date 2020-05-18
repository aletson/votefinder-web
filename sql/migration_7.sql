update migration_version set version = 7;
ALTER TABLE main_game CHANGE threadId thread_id int,
                      CHANGE lastUpdated last_updated datetime,
                      CHANGE maxPages max_pages int,
                      CHANGE currentPage current_page int;
ALTER TABLE main_post CHANGE postId post_id int,
                      CHANGE authorSearch author_search int,
                      CHANGE pageNumber page_number int;
ALTER TABLE main_vote CHANGE targetString target_string varchar(256);
ALTER TABLE main_gameday CHANGE dayNumber day_number int,
                         CHANGE startPost_id start_post int;