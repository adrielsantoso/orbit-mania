"""Game rules, checked without opening a window."""

import math

import pytest

from orbit_mania.game import (
    ANGULAR_SPEED, FUEL_DRAIN, FUEL_DRAIN_SHIELD, INNER_ORBIT, MAX_FUEL, OUTER_ORBIT,
    PACKET_FUEL, RADIUS_RATE, Game, Obstacle, Packet,
)


def test_start_at_top_of_inner_orbit():
    g = Game(seed=1)
    x, y = g.ship
    assert x == pytest.approx(0.0, abs=1e-9)
    assert y == pytest.approx(-INNER_ORBIT)


def test_ship_moves_at_constant_angular_speed_and_radius():
    g = Game(seed=1)
    for _ in range(100):
        g.step()
    assert g.angle == pytest.approx(270.0 + 100 * ANGULAR_SPEED)
    assert math.hypot(*g.ship) == pytest.approx(INNER_ORBIT)


def test_orbit_switch_takes_distance_over_rate_frames():
    g = Game(seed=1)
    g.step(switch=True)
    frames = 1
    while g.radius != g.target_radius:
        g.step()
        frames += 1
    # constant rate, then the last partial step snaps onto the orbit
    assert frames == math.ceil((OUTER_ORBIT - INNER_ORBIT) / RADIUS_RATE)
    assert g.radius == OUTER_ORBIT


def test_switch_is_ignored_while_switching():
    g = Game(seed=1)
    g.step(switch=True)
    g.step(switch=True)                     # pressed again mid-transfer
    assert g.target_radius == OUTER_ORBIT


def test_fuel_drains_faster_with_shield():
    g = Game(seed=1)
    g.step()
    assert g.fuel == pytest.approx(MAX_FUEL - FUEL_DRAIN)
    g.step(shield=True)
    assert g.fuel == pytest.approx(MAX_FUEL - FUEL_DRAIN - FUEL_DRAIN_SHIELD)


def test_running_out_of_fuel_ends_the_game():
    g = Game(seed=1)
    g.fuel = FUEL_DRAIN / 2
    g.packets.clear()
    events = g.step()
    assert events.out_of_fuel and g.over


def _obstacle_on_ship(g: Game) -> Obstacle:
    x, y = g.ship
    a = math.radians(g.angle + ANGULAR_SPEED)            # where the ship will be next frame
    return Obstacle(x=g.radius * math.cos(a), y=g.radius * math.sin(a), vx=0.0)


def test_asteroid_without_shield_crashes():
    g = Game(seed=1)
    g.obstacles.append(_obstacle_on_ship(g))
    events = g.step()
    assert events.crashed and g.over


def test_shield_destroys_asteroid():
    g = Game(seed=1)
    g.obstacles.append(_obstacle_on_ship(g))
    events = g.step(shield=True)
    assert events.obstacles_destroyed == 1
    assert not g.over
    assert g.obstacles == []


def test_energy_packet_refuels_up_to_the_maximum():
    g = Game(seed=1)
    g.fuel = 50.0
    ob = _obstacle_on_ship(g)
    g.packets.append(Packet(ob.x, ob.y))
    events = g.step()
    assert events.packets_collected == 1
    assert g.fuel == pytest.approx(50.0 - FUEL_DRAIN + PACKET_FUEL)

    g.fuel = MAX_FUEL
    ob = _obstacle_on_ship(g)
    g.packets.append(Packet(ob.x, ob.y))
    g.step()
    assert g.fuel == MAX_FUEL


def test_difficulty_ramps_over_one_minute():
    g = Game(seed=1)
    assert g.obstacle_interval() == 180
    assert g.obstacle_speed_range() == (1.0, 2.0)
    g.frame = 3600
    assert g.obstacle_interval() == 45
    assert g.obstacle_speed_range() == (2.5, 5.0)
    g.frame = 10_000                         # stays at the hardest level
    assert g.obstacle_interval() == 45


def test_asteroids_and_packets_appear_on_schedule():
    # The first asteroid comes at the first frame f with f >= interval(f); the
    # interval already shrinks during the first seconds as difficulty rises.
    g = Game(seed=1)
    probe = Game(seed=1)
    first = next(f for f in range(1, 200)
                 if (setattr(probe, "frame", f) or f >= probe.obstacle_interval()))
    for _ in range(first - 1):
        g.step()
    assert g.obstacles == []
    g.step()
    assert len(g.obstacles) == 1 and g.last_obstacle_frame == first

    while g.frame < 300:
        g.step(shield=True)                  # shield on: no crash ends the test early
        g.fuel = MAX_FUEL
    assert g.last_packet_frame == 300


def test_same_seed_same_game():
    def play(seed):
        g = Game(seed=seed)
        for i in range(2000):
            g.step(switch=(i % 240 == 0), shield=(i % 97 < 10))
            if g.over:
                break
        return g.frame, [(round(o.x, 6), round(o.y, 6)) for o in g.obstacles]

    assert play(7) == play(7)
    assert play(7) != play(8)


def test_no_input_after_game_over():
    g = Game(seed=1)
    g.over = True
    frame = g.frame
    g.step(switch=True, shield=True)
    assert g.frame == frame
