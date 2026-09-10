-- ==============================================================================
-- Telegram Video Search & Download Bot - Demo Seed Data (demo_seed.sql)
-- ==============================================================================

-- 1. Insert Sample Movie: Inception (2010)
INSERT INTO contents (id, title, normalized_title, content_type, year, original_title, description)
VALUES (1, 'Inception', 'inception', 'movie', 2010, 'Inception', 'A thief who steals corporate secrets through the use of dream-sharing technology.')
ON CONFLICT (id) DO NOTHING;

-- Movie Files (different qualities)
INSERT INTO files (id, content_id, quality, file_name, file_size_bytes, duration_seconds, audio, telegram_channel_id, telegram_message_id)
VALUES 
(1, 1, '480p', 'Inception.2010.480p.BluRay.Hindi-English.mkv', 471859200, 8880, 'Hindi + English', -1001234567890, 101),
(2, 1, '720p', 'Inception.2010.720p.BluRay.Hindi-English.mkv', 1288490188, 8880, 'Hindi + English DD5.1', -1001234567890, 102),
(3, 1, '1080p', 'Inception.2010.1080p.BluRay.Hindi-English.mkv', 2952790016, 8880, 'Hindi + English DD5.1', -1001234567890, 103)
ON CONFLICT (telegram_channel_id, telegram_message_id) DO NOTHING;

-- 2. Insert Sample Movie: Interstellar (2014)
INSERT INTO contents (id, title, normalized_title, content_type, year, original_title, description)
VALUES (2, 'Interstellar', 'interstellar', 'movie', 2014, 'Interstellar', 'When Earth becomes uninhabitable in the future, a farmer and ex-NASA pilot is tasked to pilot a spacecraft.')
ON CONFLICT (id) DO NOTHING;

INSERT INTO files (id, content_id, quality, file_name, file_size_bytes, duration_seconds, audio, telegram_channel_id, telegram_message_id)
VALUES 
(4, 2, '720p', 'Interstellar.2014.720p.BluRay.DualAudio.mkv', 1500000000, 10140, 'Hindi + English', -1001234567890, 104),
(5, 2, '1080p', 'Interstellar.2014.1080p.BluRay.DualAudio.mkv', 3400000000, 10140, 'Hindi + English DD5.1', -1001234567890, 105)
ON CONFLICT (telegram_channel_id, telegram_message_id) DO NOTHING;

-- 3. Insert Sample Series: Breaking Bad (2008)
INSERT INTO contents (id, title, normalized_title, content_type, year, original_title, description)
VALUES (3, 'Breaking Bad', 'breaking bad', 'series', 2008, 'Breaking Bad', 'A chemistry teacher diagnosed with inoperable lung cancer turns to manufacturing and selling methamphetamine.')
ON CONFLICT (id) DO NOTHING;

-- Breaking Bad Seasons
INSERT INTO seasons (id, content_id, season_number, title)
VALUES 
(1, 3, 1, 'Season 1'),
(2, 3, 2, 'Season 2')
ON CONFLICT (content_id, season_number) DO NOTHING;

-- Season 1 Episodes
INSERT INTO episodes (id, season_id, episode_number, title, normalized_title, duration_seconds)
VALUES 
(1, 1, 1, 'Pilot', 'pilot', 3480),
(2, 1, 2, 'Cat''s in the Bag...', 'cats in the bag', 2880)
ON CONFLICT (season_id, episode_number) DO NOTHING;

-- Season 1 Episode 1 Files
INSERT INTO files (id, content_id, episode_id, quality, file_name, file_size_bytes, duration_seconds, audio, telegram_channel_id, telegram_message_id)
VALUES 
(6, 3, 1, '480p', 'Breaking.Bad.S01E01.480p.mkv', 180000000, 3480, 'Hindi', -1001234567890, 201),
(7, 3, 1, '720p', 'Breaking.Bad.S01E01.720p.mkv', 450000000, 3480, 'Hindi + English', -1001234567890, 202),
(8, 3, 1, '1080p', 'Breaking.Bad.S01E01.1080p.mkv', 980000000, 3480, 'Hindi + English DD5.1', -1001234567890, 203)
ON CONFLICT (telegram_channel_id, telegram_message_id) DO NOTHING;

-- Season 1 Episode 2 Files
INSERT INTO files (id, content_id, episode_id, quality, file_name, file_size_bytes, duration_seconds, audio, telegram_channel_id, telegram_message_id)
VALUES 
(9, 3, 2, '720p', 'Breaking.Bad.S01E02.720p.mkv', 430000000, 2880, 'Hindi + English', -1001234567890, 204),
(10, 3, 2, '1080p', 'Breaking.Bad.S01E02.1080p.mkv', 950000000, 2880, 'Hindi + English DD5.1', -1001234567890, 205)
ON CONFLICT (telegram_channel_id, telegram_message_id) DO NOTHING;

-- Reset sequences
SELECT setval('contents_id_seq', (SELECT MAX(id) FROM contents));
SELECT setval('seasons_id_seq', (SELECT MAX(id) FROM seasons));
SELECT setval('episodes_id_seq', (SELECT MAX(id) FROM episodes));
SELECT setval('files_id_seq', (SELECT MAX(id) FROM files));
