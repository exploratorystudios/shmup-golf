# shmupgolf.py

> *the cave is not on your side.*

---

it's a horizontal shoot-em-up compressed into 7 lines of Python. no semicolons. each line is one logical statement. what each statement *does* is a separate and longer conversation.

`shmupgolf_unobfuscated.py` is in this repo. that's the one you read. the compressed version is for looking at. you look at it. you feel something. you close it.

---
You can also play on this website: https://shmupgolf.fly.dev/

## Running It

```bash
python shmupgolf.py
```

**linux:** install xlib for hardware-level key polling. without it the curses fallback works but held keys have that classic OS repeat-rate stutter.
```bash
pip install xlib
```

**windows:**
```bash
pip install windows-curses
```

make your terminal large. the game is a cave and caves need space.

---

## Controls

| key | action |
|-----|--------|
| up / W | fly up |
| down / S | fly down |
| space | shoot |

---

## The Game

you are `⠶⠄` on linux, `▐-` on windows. two characters. that's the ship. it sits at column 3 and the world scrolls past it.

**the cave** is a ceiling and a floor that each wander by random walk every frame, clamped so they can't take up more than the top or bottom third of the screen. they do not coordinate with each other. sometimes the passage is generous. sometimes it is not. there is no music to warn you.

**the enemies** all share the same four-field list structure: x position, y position, type, HP. behavior is where they diverge.

- slow type (type 0): 3 HP, moves left 1 per frame. takes three shots. its sprite degrades visually as damage accumulates, going from `⣾⣷` to `⣮⣧` to `⣸⡷` on linux (`▓▓` `▒▓` `░▒` on windows). it looks worse and worse. frankly, it shows.
- fast type (type 1): 1 HP, moves left 2 per frame. one shot. you almost feel bad.
- sine-wave type (type 2): 1 HP, y position recalculated every frame as `round(sin(x * 0.4) * 2)`, clamped to the open cave at its column. things go up and down for it. but it never leaves you behind

every enemy has a 1-in-61 chance per frame to fire a bullet at you. their bullets are `◂` and move left 3 per frame. yours are `─` and move right 2. theirs are faster. just so you know.

**the spikes** spawn at the right edge, scroll left with everything else, and kill you instantly. `│` body, `▼` or `▲` tip depending on whether they drop from the ceiling or rise from the floor. they do not move independently. they are just there, in the way, committed to their position.

**the powerup** drops from destroyed enemies at a 1-in-16 chance. `⣰` on linux, `»` on windows. collecting it activates 120 frames of shield and autofires every 3 ticks. while powered up, you are shielded, and the player reaches their Final Form, `⠶⠗` / `▐=`, and the HUD reads RAPID. an enemy bullet absorbed by the shield scores 10 points and zeroes the shield. that's the only defensive mechanic. find the powerups. try to stay in this state. it's the best state to be in.

---

## Scoring

| event | points |
|-------|--------|
| hitting an enemy | 25 |
| shield absorbing a bullet | 10 |
| overlapping a powerup | 5 per frame |
| each frame alive | 1 |

---

## How The Lines Work

the compressed file is 7 lines. here's what each one actually contains.

**line 1** is the function signature. it has five default arguments. three of them are module imports (`curses`, `random.randint`, `math.sin`), evaluated once at definition time. one is a mutable list `[0]` used as the last-fire timestamp for bullet cooldown. the fifth is the entire input system: a three-way ternary that at definition time picks between windows (`GetAsyncKeyState` via ctypes, plus msvcrt buffer drain for arrow key escape sequences), linux with xlib (`query_keymap` against actual hardware state), and a plain curses fallback. all three paths are wrapped in rising-edge detection so tapping space fires once, not once per frame it's held. this is the function signature.

**line 2** is one assignment unpacking twelve variables. before the assignment resolves, the right-hand side has called `nodelay`, `start_color`, `use_default_colors`, initialized seven color pairs, hidden the cursor, captured the platform flag via walrus, conditionally called `chcp 65001` on windows so the unicode renders instead of crashing, read terminal size, and generated both the ceiling and floor arrays as full random walks. twelve variables. all of that setup. one line.

**line 3** is `while 1:`.

**line 4** reads input and updates the world state. it reads the direction key and fire state, clamps movement to the cave at the player's column, fires a bullet if space was tapped and the cooldown has elapsed, autofires every 3 ticks if shielded, scrolls both terrain arrays one step, moves and culls spikes, randomly spawns new spikes, spawns slow/fast enemies every 30 ticks via an IIFE that rolls the type once and uses it for both the type field and the HP value, spawns sine-wave enemies every 27 ticks, and gives every enemy a chance to fire back. the whole expression returns the new `(player_y, shield_timer, score)` as a tuple.

**line 5** is the physics and collision line. it moves everything: player bullets right by 2, enemy bullets left by 3, slow enemies left by 1, fast enemies left by 2, sine-wave enemies by the sin function clamped to the cave, powerups left by 1. it computes which enemies were hit by which bullets using walrus-bound sets, decrements HP, scores 25 per hit, drops powerups from newly zeroed enemies, removes dead and off-screen enemies, removes spent bullets. it handles powerup collection, sets the shield to 120 frames, scores the proximity bonus. it detects enemy bullet hits, absorbs them via shield or clears the player's bullets on a fatal hit. then the `not[...]` block resolves false, the `or` fires, and it checks five death conditions: ceiling, floor, spike, enemy body, unshielded bullet. if any are true it draws GAME OVER, shows the score, waits 2.5 seconds, and exits. all of that is one statement.

**line 6** erases the screen, then draws in nine passes: the open-cave corridor line along the player's row, ceiling and floor tiles, the parallax starfield (W//4 stars at hash-based fixed positions, scrolling at t//13, with braille sub-pixel animation on linux that alternates `⠠` and `⠄` to simulate half-cell leftward movement within a character that doesn't actually support sub-positions), spikes with their directional tips, enemies with HP-sensitive sprites in linux/windows variants, enemy bullets with per-frame color alternation, player bullets, powerups, and the player itself. then the HUD: zero-padded score and RAPID with lightning bolts when shielded. then `s.refresh()`, tick increment via walrus, and `c.napms(90)`.

**line 7** is `__import__("curses").wrapper(g)`.

one note on the render chain: `s.erase()` returns `None`, which is falsy, so `or not[...draws...]` runs. the draw calls are wrapped in `not[...]` because a non-empty list is truthy and would short-circuit the chain before `s.refresh()` ever ran. `not` of any non-empty list is `False`, so the chain always continues. this is the kind of thing you find out by running the game and seeing a blank screen.

---

## Requirements

- Python 3.8+
- terminal with color support
- `windows-curses` on windows
- `xlib` on linux

---

*7 lines. the cave wanders. everything shoots.*
