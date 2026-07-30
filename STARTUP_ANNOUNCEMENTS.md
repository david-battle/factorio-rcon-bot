# Startup Announcement History

This is the durable developer/operator history of Jimbo's player-visible change
announcements. Jimbo does not expose this file in-game. At runtime,
`last_startup_summary.txt` retains only the newest summary and generic restarts
say only that Jimbo is online.

## Maintenance

Whenever `startup_change_summary` changes, append its exact new text here in the
same edit, under the current date. Record each distinct change summary once; do
not add generic unchanged-summary restarts. The always-loaded requirement is
also in `AGENTS.md`.

The entries through 2026-07-29 were recovered from the live Factorio server log.
Times are the observed server-chat timestamps. Two early entries predate the
handcrafted-summary mechanism and were generated from Git changes by the model;
they are retained because players actually saw them. Intermediate summaries
found only in Git, with no matching broadcast in the available log, are not
listed as announcements.

## 2026-07-26

- **16:33:44 — model-generated:** New build on the line! Jimbo’s been upgraded
  to OpenAI and had its spontaneous comments tuned up—fewer noisy inserters,
  more useful little quips. 🚀
- **20:52:54 — model-generated:** Hi folks, Jimbo is back online and listening
  after the update! I got a small refresh to make my startup greeting more
  reliable, so I should be ready to help again.
- **20:55:42:** Startup greetings now use handcrafted change summaries, so I can
  explain the intent of each update more accurately.
- **21:15:01:** Returning players now get fresh greetings instead of the same
  canned reply, and I recover more safely if the server log connection is
  interrupted.
- **21:36:08:** Stale conversation context now clears itself after repeated
  missed comments, or on demand when someone tells me to forget all previous
  instructions.
- **21:45:20:** Temporary AI service errors now get a couple of automatic retries
  before I give up on a response.
- **21:54:45:** I now interpret server time results as elapsed game time instead
  of confusing them with the current time of day.

## 2026-07-27

- **06:31:41:** I now reconnect automatically if the Factorio server restarts,
  so I can keep answering and greeting players without needing my own restart.
- **07:46:26:** I now count join greetings as recent activity, so I won't
  immediately welcome the same player a second time in a spontaneous comment.
- **09:09:36:** I now remember a small window of shared chat, including my own
  replies, so I can understand follow-up questions even after I restart.
- **09:12:08:** I now recognize dlbattle as the server owner when welcoming them
  back.
- **09:15:39:** I now use dlbattle as the configured server owner everywhere.
- **09:29:08:** My AI model and provider can now be switched together from one
  setting.
- **21:46:17:** After answering directly, I now retire the recent chat backlog so
  I don't repeat it in a spontaneous comment.
- **21:51:20:** I now run requested Factorio actions instead of merely claiming
  they're underway, and direct answers no longer repeat spontaneously.

## 2026-07-28

- **06:32:25:** I now stay quiet when nobody is online and mention stalled
  research only once instead of repeating unchanged progress updates.
- **14:46:04:** I now report the actual level of repeatable research instead of
  mistaking its internal prototype suffix for the level.
- **14:51:49:** I now use concise player-facing names like
  mining-productivity-8 for repeatable research.
- **14:58:36:** I now use natural player-facing names like mining productivity 8
  for repeatable research.
- **15:11:26:** I can now look up recipe ingredients using Factorio's current
  API.
- **15:20:43:** I now distinguish a planet list from the actual source of
  specific materials.
- **15:31:46:** I now handle live logistic inventory questions instead of
  dropping them as an unknown request type.
- **15:38:34:** I now use Factorio's lowercase internal planet names when
  checking remote logistic networks.
- **15:45:08:** I now acknowledge failed requests instead of silently dropping
  them.
- **15:52:22:** I can now check requested items across logistic networks on any
  planet.
- **15:57:32:** I now recognize questions about items being available or in stock
  on a planet as logistic network checks.
- **16:08:21:** I now report logistic stock as nonnegative availability and
  compare it with the amount actually required.
- **16:14:20:** I can now check logistic availability across every planet instead
  of only one.

## 2026-07-29

- **06:30:43:** I now identify the actual level of repeatable research, including
  Scrap Recycling Productivity.
- **14:08:17:** I'm preparing production-cell placement: item-only recipes at
  supplied map locations are now checked for space, power, and logistics before
  any building, chest, inserter, or pole ghosts are placed. I also clean up
  model-call temporary files now so they can't fill server storage.
- **15:37:32:** I can now handle requests to place item-only production cells at supplied map pings, reporting the verified cell or explaining why placement was rejected.
- **15:54:03:** I can now bridge short power gaps for production cells with up to two fully checked extension poles, rolling back the whole plan if any ghost fails.
- **16:10:20:** I can now find nearby clear locations for production cells from your current view, your physical position, a named direction, or the planet spawn while keeping every existing placement check.
- **16:32:46:** I can now place production cells on Aquilo when every freezable component is beside a live heat source, and I recheck that heat immediately before placing anything.
- **16:51:00:** I can now fit Aquilo production cells inside compact heated rings, using the surrounding roboport and existing electric coverage instead of forcing my standard pole layout.
- **17:36:27:** I can now place directional production cells relative to either
  where you're standing or your current map view, so requests like north of your
  current location use the intended origin.
- **17:52:30:** I now prefer fully connected production-cell sites but can still
  place a structurally safe cell when heat, power, logistics, or construction
  coverage is missing, and I'll report exactly what needs attention.
- **18:10:28:** I no longer silently drop messages that directly address me, and
  production-cell searches now record why candidate sites were rejected.

## 2026-07-30

- **13:47:** Spontaneous comments are now every 20 minutes instead of 10.
  I will no longer parrot or just rephrase what players just said.
- **13:??:** I can now tag entities on the map: just ask me to tag artillery,
  poles, roboports, or any entity type on a named surface.
- **15:??:** I can now remove chart tags: just ask me to untag artillery, poles,
  roboports, or any entity type on a named surface.
- **15:??:** I can now find and tag the entity with the highest damage dealt
  on a surface. Ask me to show the top damage for artillery or other entities.
- **16:35:** I can now find and tag the machine with the most products finished,
  as well as the entity with the highest damage dealt. Just ask me!
