# Team marks

The 32 PNG files are bundled copies of the `team_logo_espn` images identified by
the [nflverse team graphics index](https://github.com/nflverse/nflverse-pbp/blob/master/teams_colors_logos.csv),
retrieved on September 21, 2026. [nflreadr documents this index](https://nflreadr.nflverse.com/reference/load_teams.html)
as its source for team graphics. `sources.json` records the exact ESPN CDN URL
and SHA-256 digest of each unmodified file. Team marks belong to their respective
owners; this directory does not assert ownership or grant a separate logo license.

The app embeds these assets as PNG data URIs, so rendering a header requires no
external image request. Keep the assets alongside the Python source when deploying.
To update a mark, replace its PNG from the index and update its source and digest.

These are franchise marks, not a complete archive of every logo redesign.
The helper deliberately uses neutral abbreviations where a bundled modern mark
would represent a materially different identity or unverified historical design:

| Team | Seasons using a neutral mark | Mark |
| --- | --- | --- |
| Rams | Through 2015 / 2016–2019 | STL / LA |
| Chargers | Through 2016 / 2017–2019 | SD / LAC |
| Washington | Before 2022, including the 2020–2021 Football Team | WAS |
| Titans | Before the 2026 redesign | TEN |

The nflverse index maps Oakland and Las Vegas to the same Raiders shield, which
is used for both identities. Its `STL` entry resolves to the modern Los Angeles
mark, so it is not used for St. Louis seasons. The current Titans mark is the
[2026 logo recorded by nflverse](https://github.com/nflverse/nflverse-pbp/issues/100).
Unknown teams or missing assets also use a neutral text fallback.
