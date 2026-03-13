import curses
import random
import math
import os

# --------------------------------------------------
# Input handling (cross-platform)
# --------------------------------------------------

def get_input_handler(stdscr):
    """
    Returns a handler() function that returns (lk, k):
      lk: directional key held (259=up/W, 258=down/S, -1=none)
      k:  32 if space was just pressed this frame (rising edge), else -1
    """
    state = [set()]  # state[0] = previously pressed keys (for rising-edge detection)

    if os.name == 'nt':
        import msvcrt
        from ctypes import windll
        GetAsyncKeyState = windll.user32.GetAsyncKeyState

        def poll():
            keys = set()
            if GetAsyncKeyState(0x26) & 0x8000:
                keys.add(259)  # up arrow
            if GetAsyncKeyState(0x28) & 0x8000:
                keys.add(258)  # down arrow
            if GetAsyncKeyState(0x20) & 0x8000:
                keys.add(32)   # space
            while msvcrt.kbhit():
                ch = msvcrt.getch()
                if ch in (b'\xe0', b'\x00'):
                    ch = msvcrt.getch()
                k = {b'H': 259, b'P': 258, b' ': 32}.get(ch, -1)
                if k != -1:
                    keys.add(k)
            return keys

    else:
        try:
            from Xlib.display import Display
            d = Display()

            def poll():
                keys = set()
                keymap = d.query_keymap()
                for sym, keysym in zip([259, 258, 32], [0xff52, 0xff54, 0x20]):
                    code = d.keysym_to_keycode(keysym)
                    if keymap[code >> 3] & (1 << (code & 7)):
                        keys.add(sym)
                while True:
                    ch = stdscr.getch()
                    if ch == -1:
                        break
                    keys.add(ch)
                return keys

        except ImportError:
            def poll():
                keys = set()
                while True:
                    ch = stdscr.getch()
                    if ch == -1:
                        break
                    keys.add(ch)
                return keys

    def handler():
        current = poll()

        # rising-edge detection for space (fire only on first frame of press)
        fire = 32 in current and 32 not in state[0]
        state[0] = current

        # up/down: also accept W/S keys (keycodes 119 and 115)
        if 259 in current or 119 in current:
            lk = 259
        elif 258 in current or 115 in current:
            lk = 258
        else:
            lk = -1

        k = 32 if fire else -1
        return lk, k

    return handler


# --------------------------------------------------
# Main game
# --------------------------------------------------

def game(stdscr):
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()

    NT = os.name == 'nt'
    if NT:
        os.system('chcp 65001>nul 2>&1')

    # Color pairs:
    # 1=cave walls (grey), 2=player (cyan), 3=enemies/enemy bullets (red),
    # 4=player bullets (yellow), 5=powerups (magenta), 6=corridor (dark grey), 7=stars (white)
    for i, col in enumerate([246, 51, 196, 226, 201, 238, 231]):
        curses.init_pair(i + 1, col, -1)

    stdscr.nodelay(True)

    H, W = stdscr.getmaxyx()
    H -= 1

    # Generate initial cave (ceiling and floor heights at each column)
    ceiling = [3] * W
    floor_h = [3] * W
    for x in range(1, W):
        ceiling[x] = max(2, min(H // 3, ceiling[x - 1] + random.randint(-1, 1)))
        floor_h[x] = max(2, min(H // 3, floor_h[x - 1] + random.randint(-1, 1)))

    player_y = H // 2
    score = 0
    shield = 0      # frames of shield + rapid-fire remaining (pw)
    tick = 0
    last_fire = 0   # tick of last player shot (_lf)

    bullets = []        # player bullets:  [x, y]
    enemy_bullets = []  # enemy bullets:   [x, y]
    enemies = []        # [x, y, type, hp]
                        #   type 0: slow (1px/frame, 3 HP)
                        #   type 1: fast (2px/frame, 1 HP)
                        #   type 2: sine-wave (2px/frame, 1 HP, y follows sine)
    powerups = []       # [x, y]  — dropped by killed enemies
    spikes = []         # [x, direction, length]
                        #   direction 0 = hangs from ceiling, 1 = rises from floor

    input_handler = get_input_handler(stdscr)

    while True:
        lk, k = input_handler()

        # Player movement (clamped to open cave space at column 3)
        ct, cf = ceiling[3], floor_h[3]
        if lk == 259:
            player_y = max(ct + 1, player_y - 1)
        elif lk == 258:
            player_y = min(H - cf - 2, player_y + 1)

        # Decrement shield each frame
        shield = max(0, shield - 1)

        # Per-frame survival score
        score += 1

        # Fire player bullet (rising-edge space + 5-tick cooldown)
        if k == 32 and tick - last_fire >= 5:
            bullets.append([3, player_y])
            last_fire = tick

        # Auto-fire when shielded (rapid-fire every 3 ticks)
        if shield > 0 and tick % 3 == 0:
            bullets.append([3, player_y])

        # Scroll terrain: pop leftmost column, generate new rightmost
        ceiling.pop(0)
        floor_h.pop(0)
        ceiling.append(max(2, min(H // 3, ceiling[-1] + random.randint(-1, 1))))
        floor_h.append(max(2, min(H // 3, floor_h[-1] + random.randint(-1, 1))))

        # Move spikes leftward, discard off-screen
        spikes = [[x - 1, d, l] for x, d, l in spikes if x > 0]

        # Spawn spike (~1-in-13 chance per frame)
        if random.randint(0, 12) == 0:
            spikes.append([W - 1, random.randint(0, 1), random.randint(1, 3)])

        # Spawn slow/fast enemy every 30 ticks
        if tick % 30 == 0:
            etype = random.randint(0, 1)
            ey = random.randint(ceiling[-1] + 1, max(ceiling[-1] + 2, H - floor_h[-1] - 2))
            enemies.append([W - 2, ey, etype, 3 if etype == 0 else 1])

        # Spawn sine-wave enemy (type 2) every 27 ticks
        if tick % 27 == 0:
            ey = random.randint(ceiling[-1] + 1, max(ceiling[-1] + 2, H - floor_h[-1] - 2))
            enemies.append([W - 2, ey, 2, 1])

        # Enemy fire: non-sine enemies shoot ~1-in-61 chance per frame
        for e in enemies:
            if random.randint(0, 60) == 0 and e[2] != 2:
                enemy_bullets.append([e[0] - 1, e[1]])

        # --- Physics ---

        # Move player bullets (+2 per frame)
        bullets = [[x + 2, y] for x, y in bullets if x + 2 < W - 1]

        # Move enemy bullets (-3 per frame)
        enemy_bullets = [[x - 3, y] for x, y in enemy_bullets if x > -1]

        # Move enemies
        for e in enemies:
            # type 0: 1px/frame; types 1 and 2: 2px/frame
            e[0] -= 1 if e[2] == 0 else 2
            if e[2] == 2:
                # Sine-wave y update, clamped to open cave at enemy's column
                cx = min(e[0], len(ceiling) - 1)
                e[1] = max(
                    ceiling[cx] + 1,
                    min(H - floor_h[cx] - 2,
                        e[1] + round(math.sin(e[0] * 0.4) * 2))
                )

        # Move powerups (-1 per frame)
        powerups = [[x - 1, y] for x, y in powerups if x > 0]

        # --- Collision detection ---

        # Which enemies were hit by player bullets
        hit_enemies = {
            i for i, e in enumerate(enemies)
            for bx, by in bullets
            if e[1] == by and e[0] - 1 <= bx <= e[0] + 2
        }
        # Which player bullets hit an enemy
        hit_bullets = {
            i for i, (bx, by) in enumerate(bullets)
            for e in enemies
            if by == e[1] and e[0] - 1 <= bx <= e[0] + 2
        }

        # Apply damage and score
        for i in hit_enemies:
            enemies[i][3] -= 1
        score += 25 * len(hit_enemies)

        # Spawn powerup when enemy HP reaches 0 (~1-in-16 chance)
        for i in hit_enemies:
            if enemies[i][3] <= 0 and random.randint(0, 15) == 0:
                powerups.append([enemies[i][0], enemies[i][1]])

        # Remove dead or off-screen enemies, and spent bullets
        enemies = [e for i, e in enumerate(enemies) if (i not in hit_enemies or e[3] > 0) and e[0] > 0]
        bullets = [b for i, b in enumerate(bullets) if i not in hit_bullets]

        # Powerup pickup: score per-frame overlap, then grant shield on collection
        score += 5 * sum(1 for x, y in powerups if abs(x - 3) < 2 and y == player_y)
        shield = max(shield, 120 * int(any(abs(x - 3) < 2 and y == player_y for x, y in powerups)))
        powerups = [p for p in powerups if not (abs(p[0] - 3) < 2 and p[1] == player_y)]

        # Enemy bullet hit detection
        hit = any(3 <= x <= 4 and y == player_y for x, y in enemy_bullets)
        score += 10 * int(hit)
        shielded = shield > 0 and hit
        if hit:
            shield = 0  # shield consumed on any hit
        if hit and not shielded:
            bullets.clear()  # cleanup before death
        # Remove enemy bullets that reached the player
        enemy_bullets = [e for e in enemy_bullets if not (2 <= e[0] <= 4 and e[1] == player_y)]

        # --- Death check ---
        dead = (
            # Flew into cave wall (check columns 3 and 4)
            any(player_y < ceiling[3 + d] or player_y >= H - floor_h[3 + d] for d in [0, 1])
            # Hit a spike at the player's column range
            or any(
                3 <= sx <= 4 and sx < len(ceiling) and (
                    (d == 0 and ceiling[sx] <= player_y < ceiling[sx] + l)
                    or (d == 1 and H - floor_h[sx] - l <= player_y < H - floor_h[sx])
                )
                for sx, d, l in spikes
            )
            # Collided with an enemy
            or any(3 <= e[0] <= 4 and e[1] == player_y for e in enemies)
            # Hit by unshielded enemy bullet
            or (hit and not shielded)
        )

        if dead:
            stdscr.addstr(H // 2, W // 2 - 5, "GAME OVER!")
            stdscr.addstr(H // 2 + 1, W // 2 - 5, f"Score:{score}")
            stdscr.refresh()
            curses.napms(2500)
            return

        # --- Render ---
        stdscr.erase()

        # Open corridor at player row (keeps player row clear of terrain tiles)
        for x in range(5, W - 1):
            if ceiling[x] < player_y < H - floor_h[x]:
                stdscr.addstr(player_y, x, '─', curses.color_pair(6))

        # Cave walls: ceiling and floor tiles
        for col in range(W):
            for row in list(range(ceiling[col])) + list(range(H - floor_h[col], H)):
                if 0 <= row < H:
                    stdscr.addstr(row, col, '░', curses.color_pair(1))

        # Starfield: parallax, sub-pixel animation on Linux
        for i in range(W // 4):
            sx = i * 4
            sy = (i * 2654435761 + i * i * 12345 >> 14) % H
            cx = (sx - tick // 13) % W
            if 0 <= sy < H and 0 <= cx < W and ceiling[cx] < sy < H - floor_h[cx]:
                ch = '·' if NT else ('⠠' if tick % 13 < 7 else '⠄')
                stdscr.addstr(sy, cx, ch, curses.color_pair(7))

        # Spikes (│ body, ▼/▲ tip)
        for sx, d, l in spikes:
            if 0 < sx < W and sx < len(ceiling):
                rows = range(ceiling[sx], ceiling[sx] + l) if d == 0 else range(H - floor_h[sx] - l, H - floor_h[sx])
                for row in rows:
                    if 0 <= row < H:
                        if d == 0 and row == ceiling[sx] + l - 1:
                            ch = '▼'
                        elif d == 1 and row == H - floor_h[sx] - l:
                            ch = '▲'
                        else:
                            ch = '│'
                        stdscr.addstr(row, sx, ch, curses.color_pair(1))

        # Enemies (sprite varies by type and remaining HP)
        for e in enemies:
            if 0 < e[0] < W - 2 and 0 < e[1] < H:
                if e[2] == 0:   # slow enemy: visually degrades as HP drops
                    if e[3] == 1:
                        ch = '░▒' if NT else '⣸⡷'
                    elif e[3] == 2:
                        ch = '▒▓' if NT else '⣮⣧'
                    else:
                        ch = '▓▓' if NT else '⣾⣷'
                elif e[2] == 1:  # fast enemy
                    ch = '▐▌' if NT else '⡱⢎'
                else:            # sine-wave enemy
                    ch = '▒░' if NT else '⡿⢿'
                stdscr.addstr(e[1], e[0], ch, curses.color_pair(3))

        # Enemy bullets (alternating color each frame)
        for x, y in enemy_bullets:
            if 0 < x < W - 1 and 0 < y < H:
                stdscr.addstr(y, x, '◂', curses.color_pair(3 if tick % 2 < 1 else 7))

        # Player bullets
        for x, y in bullets:
            if 0 < x < W - 1 and 0 < y < H:
                stdscr.addstr(y, x, '─', curses.color_pair(4))

        # Powerups
        for x, y in powerups:
            if 0 < x < W - 1 and 0 < y < H:
                stdscr.addstr(y, x, '»' if NT else '⣰', curses.color_pair(5))

        # Player ship (powered-up sprite when shielded)
        ship = ('▐=' if NT else '⠶⠗') if shield > 0 else ('▐-' if NT else '⠶⠄')
        stdscr.addstr(player_y, 3, ship, curses.color_pair(2))

        # HUD
        stdscr.addstr(0, 1, f'Score:{score:05d}' + (' ⚡RAPID⚡' if shield > 0 else ''), curses.A_BOLD)

        stdscr.refresh()
        tick += 1
        curses.napms(90)


# --------------------------------------------------
# Entry
# --------------------------------------------------

curses.wrapper(game)
