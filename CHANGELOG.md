## Changelog

### 3.0 _(planned)_
- Migrate to Python 3 and more modern libraries
- Images are now parsed into click-to-show format in posts.

### 2.2 _(planned)_
- Send PM's through the Votefinder application
- Moderators are able to add loved/hated stacks to a player
- Moderators can add votes that are only moderator-visible until hammer
- Adds support for players with multiple votes natively

### 2.1 _(planned)_
- Fix cases where the application fails silently
- Add filtering to player and closed game list
- Fix performance on closed game list page
- Generate "games in signup" image and provide a mechanism for automatically signing up for games

### 2.0.3
- Refresh player list and votecount when players are removed or added
- Fix for #51

### 2.0.2
- Add debug mode to environment-set settings
- Feature: Add anonymous vote to all players
- Fix broken components on posts tab
- Remove deprecated code
- Simplify some queries
- Brings back underline styling for active votes


### 2.0.1
- Remove URL shortening code (unused)
- Migrate to environment variables for site configuration
- Parses italics and quotes in posts
- Add stylesheet easter egg
- Miscellaneous style fixes
- Fixes for non-working buttons after 2.0 release
- Fixes for inconsistent votecount post
- Fixes for "NameError" when setting deadlines
- Fixes for 500 error on game creation

### 2.0
- Redevelop into responsive design using Bootstrap
- Update jQuery and jQuery UI library version
- Make page components usable on mobile
- Quicker loads on player page
- Update Pillow

### Before versioning
- 
- Migration to HTTPS
- Add votecount to hammer post
- Upgrade to Django 1.11 from 1.2
- Ecco Mode: Players must not have an active vote before voting again
- Added password reset / forgotten password
