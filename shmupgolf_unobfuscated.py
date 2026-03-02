import curses
import random
import math
import os
import time

# --------------------------------------------------
# Input handling (cross-platform)
# --------------------------------------------------

def get_input_handler(stdscr):
    pressed = set()

    if os.name == "nt":
        import msvcrt
        from ctypes import windll

        def poll():
            keys = set()

            if windll.user32.GetAsyncKeyState(0x26) & 0x8000:  # Up
                keys.add(259)
            if windll.user32.GetAsyncKeyState(0x28) & 0x8000:  # Down
                keys.add(258)
            if windll.user32.GetAsyncKeyState(0x20) & 0x8000:  # Space
                keys.add(32)

            while msvcrt.kbhit():
                msvcrt.getch()

            return keys

    else:
        def poll():
            keys = set()
            while True:
                ch = stdscr.getch()
                if ch == -1:
                    break
                keys.add(ch)
            return keys

    def handler():
        nonlocal pressed
        current = poll()

        fire = 32 in current and 32 not in pressed
        pressed = current

        if 259 in current:
            return 259, fire
        if 258 in current:
            return 258, fire
        return -1, fire

    return handler


# --------------------------------------------------
# Main game
# --------------------------------------------------

def game(stdscr):
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()

    for i, col in enumerate([246, 51, 196, 226, 201, 238, 231]):
        curses.init_pair(i + 1, col, -1)

    stdscr.nodelay(True)

    H, W = stdscr.getmaxyx()
    H -= 1

    player_y = H // 2
    score = 0
    shield = 0
    tick = 0

    bullets = []
    enemy_bullets = []
    enemies = []
    powerups = []
    spikes = []

    ceiling = [3] * W
    floor = [3] * W

    for x in range(1, W):
        ceiling[x] = max(2, min(H // 3, ceiling[x - 1] + random.randint(-1, 1)))
        floor[x] = max(2, min(H // 3, floor[x - 1] + random.randint(-1, 1)))

    input_handler = get_input_handler(stdscr)
    last_fire = 0

    while True:
        key, fire = input_handler()

        # Player movement
        if key == 259:
            player_y = max(ceiling[3] + 1, player_y - 1)
        elif key == 258:
            player_y = min(H - floor[3] - 2, player_y + 1)

        # Fire bullets
        if fire and tick - last_fire > 5:
            bullets.append([3, player_y])
            last_fire = tick

        # Auto-fire when shielded
        if shield > 0 and tick % 3 == 0:
            bullets.append([3, player_y])

        # Scroll terrain
        ceiling.pop(0)
        floor.pop(0)
        ceiling.append(max(2, min(H // 3, ceiling[-1] + random.randint(-1, 1))))
        floor.append(max(2, min(H // 3, floor[-1] + random.randint(-1, 1))))

        # Move bullets
        bullets = [[x + 2, y] for x, y in bullets if x + 2 < W - 1]
        enemy_bullets = [[x - 3, y] for x, y in enemy_bullets if x > 0]

        # Spawn enemies
        if random.randint(0, 12) == 0:
            enemies.append([W - 1, random.randint(0, 1), random.randint(1, 3), 3])

        # Move enemies
        for e in enemies:
            if e[1] == 0:
                e[0] -= 1
            elif e[1] == 1:
                e[0] -= 2
            else:
                cx = min(e[0], W - 1)
                e[1] = max(
                    ceiling[cx] + 1,
                    min(H - floor[cx] - 2,
                        e[1] + round(math.sin(e[0] * 0.4) * 2))
                )

        # Bullet hits
        hit_enemies = {
            i for i, e in enumerate(enemies)
            for bx, by in bullets
            if by == e[1] and e[0] - 1 <= bx <= e[0] + 2
        }

        for i in hit_enemies:
            enemies[i][3] -= 1

        score += 25 * len(hit_enemies)

        # Spawn powerups
        for i in hit_enemies:
            if enemies[i][3] <= 0 and random.randint(0, 15) == 0:
                powerups.append([enemies[i][0], enemies[i][1]])

        enemies = [
            e for i, e in enumerate(enemies)
            if i not in hit_enemies or e[3] > 0
        ]

        bullets = [
            b for i, b in enumerate(bullets)
            if not any(
                by == enemies[j][1] and enemies[j][0] - 1 <= bx <= enemies[j][0] + 2
                for j in hit_enemies
                for bx, by in [b]
            )
        ]

        # Powerup pickup
        for p in powerups:
            if abs(p[0] - 3) < 2 and p[1] == player_y:
                shield = 120

        powerups = [
            p for p in powerups
            if not (abs(p[0] - 3) < 2 and p[1] == player_y)
        ]

        # Enemy bullets
        for e in enemies:
            if random.randint(0, 60) == 0:
                enemy_bullets.append([e[0] - 1, e[1]])

        hit = any(3 <= x <= 4 and y == player_y for x, y in enemy_bullets)

        if hit:
            if shield > 0:
                score += 10
                shield = 0
            else:
                break

        # Draw
        stdscr.erase()

        for x in range(W):
            for y in range(ceiling[x]):
                stdscr.addstr(y, x, "░", curses.color_pair(1))
            for y in range(H - floor[x], H):
                stdscr.addstr(y, x, "░", curses.color_pair(1))

        for x, y in bullets:
            stdscr.addstr(y, x, "─", curses.color_pair(4))

        for x, y in enemy_bullets:
            stdscr.addstr(y, x, "◂", curses.color_pair(7))

        for e in enemies:
            stdscr.addstr(e[1], e[0], "▓▓", curses.color_pair(3))

        for p in powerups:
            stdscr.addstr(p[1], p[0], "»", curses.color_pair(5))

        stdscr.addstr(
            player_y, 3,
            "▐=" if shield else "▐-",
            curses.color_pair(2)
        )

        stdscr.addstr(
            0, 1,
            f"Score:{score:05d}" + (" ⚡RAPID⚡" if shield else ""),
            curses.A_BOLD
        )

        stdscr.refresh()

        shield = max(0, shield - 1)
        tick += 1
        time.sleep(0.09)

    # Game over
    stdscr.addstr(H // 2, W // 2 - 5, "GAME OVER!")
    stdscr.addstr(H // 2 + 1, W // 2 - 5, f"Score:{score}")
    stdscr.refresh()
    time.sleep(2.5)


# --------------------------------------------------
# Entry
# --------------------------------------------------

curses.wrapper(game)
