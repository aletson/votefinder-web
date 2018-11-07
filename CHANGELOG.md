## Changelog

### 3.0 _(planned)_
- Migrate to Python 3 and more modern libraries
- Images are now parsed into click-to-show format in posts.

### 2.2 _(planned)_
- Send PM's through the Votefinder application
- Moderators are able to add loved/hated stacks to a player
- Moderators can add votes that are only moderator-visible until hammer
- Adds support for players with multiple votes natively
- Generate "games in signup" image and provide a mechanism for automatically signing up for games

### 2.2.3
- Added ability to set deadline via in-thread post
- Security fixes and package updates
- Changed credits


### 2.2.2
- Security fixes & package updates

### 2.2.1
- Fixed a bug where the "password reset complete" page would 404

### 2.2.0
- Adds theming! Now you can select themes from your profile page. Currently "default" and "yospos" available, more to come... (#53, #87)
- Various cosmetic fixes. (#47, #49, #66, #45)

### 2.1.4
- Fixes global theme display errors with Font Awesome. (#78)
- Changes default tab state based on closed / open game when a moderator.

### 2.1.3
- Fixes incorrect redirection after performing certain actions in Votefinder (#60)
- Fixes the wrong tab being active by default on game page (#65)

### 2.1.2
- Fixes no pagination on players and closed games tables

### 2.1.1
- Fix styling issues on jQuery UI related elements
- Add filtering to player list and closed games list (#41)

### 2.1
- FEATURE: Post to Amazon SQS when a game is opened
- Fix a bug where users could reregister after a SA forums name change
- Fix performance on closed game list page
- Fix 500 errors on manual vote resolution

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
