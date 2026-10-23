# Battle Chess Arena API

## Local setup

1. Create and activate a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and set `DJANGO_SECRET_KEY` to a random local secret.
4. Run `python manage.py migrate` to create the local SQLite database.
5. Start the API with `python manage.py runserver 127.0.0.1:8000`.

The health check is available at `http://127.0.0.1:8000/api/health/`.

The local development database is SQLite and is stored in `db.sqlite3`.

## Server-authoritative chess moves

Submit moves to `POST /api/matches/<match-id>/moves/` with `from`, `to`, and
optional `promotion` (`q`, `r`, `b`, or `n`). The API validates turn ownership
and move legality, generates notation and FEN, and completes the match when the
board reaches a terminal position. Client-provided notation, FEN, and results
are not used as match authority. Checkmate, stalemate, insufficient material,
the 75-move rule, and fivefold repetition end the game automatically. A player
can claim threefold repetition or the 50-move rule with
`POST /api/matches/<match-id>/claim-draw/` when the board permits it.

Quick matches queue a player for up to five minutes until another player joins;
both players receive the same active match with randomly assigned colors. The
game page polls the match state while waiting and can cancel its specific queue
entry. Once matched, authenticated WebSockets push accepted moves and game
completion to both players. If a WebSocket disconnects, the frontend falls
back to polling. The default in-memory channel layer is for local single-process
development only. Set `REDIS_URL` (for example, `redis://127.0.0.1:6379/0`) to
use Redis for multi-process deployments.

## Play vs AI

Create a match with `POST /api/matches/` using mode `ai` and an optional
`difficulty` of `beginner`, `intermediate`, or `advanced`. The API validates
the player's move, chooses and records a legal AI reply, and returns both moves
in the match history. AI search depth is bounded by difficulty and a node cap;
the AI is a lightweight built-in opponent, not a Stockfish-strength engine.

## Post-game review

Participants can request `GET /api/matches/<match-id>/review/` after a match
ends. The review replays server-recorded moves and highlights immediate
checkmates and major one-move material tactics, and identifies the reviewing
player's own mistakes. For clear position-score differences it also offers an
explorable alternative move from a lightweight positional scan. This is not a
full chess-engine evaluation or a substitute for engine-grade analysis. When
the review identifies a tactical training focus, it recommends an accessible
lesson from the player's guided course and links directly to that lesson.

## Guided chess classes

`GET /api/players/<player-id>/training/` returns the authenticated player's
saved progress through five levels from Beginner through Expert, with ten
guided lessons per level (50 lessons total). Lessons unlock one at a time in
course order; a completed lesson can be revisited. Each short lesson includes a
board position, clear objective, guided hints, and an explanation after the
correct move.
Submit a lesson move to
`POST /api/players/<player-id>/training/attempt/` with `lesson_id`, `from`, and
`to` (and optional `promotion`) to validate the answer and save lesson progress. The training page reviews up
to ten recent completed games, summarizes the most common tactical focus, and
suggests a lesson in the currently open class. Game trends guide practice
recommendations but do not change the fixed course unlock order.

## Player profile and notifications

`GET /api/players/<player-id>/profile-summary/` returns the signed-in player's
recorded match results, course completion, and earned milestone achievements.
Only finished matches with a recorded result contribute to the win/loss/draw
counts; the win-rate field is `null` until the player has a result.

`GET /api/players/<player-id>/notifications/` returns the 30 most recent
notifications and the unread count across the player's full inbox. Mark one
notification read with
`POST /api/players/<player-id>/notifications/<notification-id>/read/`, or mark
the whole inbox read with
`POST /api/players/<player-id>/notifications/read-all/`. These endpoints require
the player's bearer session, and the player ID in the URL must match that
session.

## Administrator console

Create a Django staff account with `python manage.py createsuperuser`, start
the frontend and API, and open `http://127.0.0.1:5173/Admin` directly. This
route is intentionally not linked from the player interface. Only active Django
staff accounts can sign in. The console provides player and match summaries,
player search, account suspension, and daily challenge/reward settings.
Suspending a player revokes active player sessions and blocks authenticated API
and WebSocket access. Staff can set the daily challenge goal from 1 to 20 quick
match wins and the reward from 0 to 100,000 coins. New challenges use those
settings, and changes also apply to today's existing progress without removing
wins already recorded. Admin API tokens expire after one hour.

## Google sign-in (local development)

Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `backend/.env`. Keep the
client secret on the backend only; never put it in frontend environment variables
or commit the `.env` file. Configure the Google OAuth web client with this exact
redirect URI:

```text
http://127.0.0.1:8000/api/auth/google/callback/
```

The frontend starts sign-in through the backend. After changing `.env`, restart
the Django server for the new values to load.