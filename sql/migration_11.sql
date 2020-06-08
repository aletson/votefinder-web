UPDATE migration_version SET version = 11;
ALTER TABLE `main_gamefaction` ADD COLUMN (`winning` BOOLEAN);