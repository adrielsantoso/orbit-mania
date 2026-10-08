"""Game rules of Orbit Mania, without graphics.

The planet sits at the origin. The ship circles it at a constant angular
speed on one of two orbits and can switch between them; while it moves
between orbits its radius changes at a constant rate. Asteroids drift in from
the right, energy packets appear on the orbits, and fuel drains every frame,
faster while the shield is on. The game ends when an asteroid hits the ship
without its shield, or when fuel runs out.

All distances are in pixels and all rates are per frame (the game runs at
60 frames per second).
"""

import math
import random
from dataclasses import dataclass, field

INNER_ORBIT = 125.0
OUTER_ORBIT = 225.0

MAX_FUEL = 100.0
FUEL_DRAIN = 0.05            # per frame, shield off
FUEL_DRAIN_SHIELD = 0.2      # per frame, shield on
PACKET_FUEL = 20.0           # fuel gained per energy packet

ANGULAR_SPEED = 0.8          # degrees per frame
RADIUS_RATE = 0.44           # pixels per frame while switching orbits
START_ANGLE = 270.0          # degrees; top of the inner orbit

SHIP_RADIUS = 15.0
SHIELD_RADIUS = 25.0
OBSTACLE_RADIUS = 15.0
PACKET_RADIUS = 10.0

# Difficulty rises linearly from 0 to 1 over the first minute of play.
DIFFICULTY_FRAMES = 3600
OBSTACLE_INTERVAL = (180, 45)          # frames between asteroids: start, hardest
OBSTACLE_SPEED_START = (1.0, 2.0)      # (min, max) pixels per frame at the start
OBSTACLE_SPEED_HARDEST = (2.5, 5.0)
OBSTACLE_SPAWN_X = (400, 800)
OBSTACLE_SPAWN_Y = (-300, 300)
OBSTACLE_REMOVE_X = -1000.0

PACKET_INTERVAL = 300                  # frames between energy packets
MAX_PACKETS = 5


@dataclass
class Obstacle:
    x: float
    y: float
    vx: float


@dataclass
class Packet:
    x: float
    y: float


@dataclass
class Events:
    """What happened during one frame, for sounds and effects."""
    packets_collected: int = 0
    obstacles_destroyed: int = 0
    crashed: bool = False
    out_of_fuel: bool = False

    @property
    def game_over(self) -> bool:
        return self.crashed or self.out_of_fuel


@dataclass
class Game:
    seed: int | None = None
    angle: float = START_ANGLE
    radius: float = INNER_ORBIT
    target_radius: float = INNER_ORBIT
    fuel: float = MAX_FUEL
    shield: bool = False
    frame: int = 0
    over: bool = False
    obstacles: list[Obstacle] = field(default_factory=list)
    packets: list[Packet] = field(default_factory=list)
    last_obstacle_frame: int = 0
    last_packet_frame: int = 0

    def __post_init__(self):
        self.rng = random.Random(self.seed)

    # ------------------------------------------------------------ state

    @property
    def ship(self) -> tuple[float, float]:
        a = math.radians(self.angle)
        return self.radius * math.cos(a), self.radius * math.sin(a)

    @property
    def switching(self) -> bool:
        return abs(self.radius - self.target_radius) >= 1.0

    @property
    def difficulty(self) -> float:
        return min(1.0, self.frame / DIFFICULTY_FRAMES)

    def obstacle_interval(self) -> int:
        start, hardest = OBSTACLE_INTERVAL
        return int(start - self.difficulty * (start - hardest))

    def obstacle_speed_range(self) -> tuple[float, float]:
        d = self.difficulty
        lo = OBSTACLE_SPEED_START[0] + d * (OBSTACLE_SPEED_HARDEST[0] - OBSTACLE_SPEED_START[0])
        hi = OBSTACLE_SPEED_START[1] + d * (OBSTACLE_SPEED_HARDEST[1] - OBSTACLE_SPEED_START[1])
        return lo, hi

    # ------------------------------------------------------------ input

    def switch_orbit(self) -> None:
        """Head for the other orbit; ignored while already switching."""
        if not self.switching:
            self.target_radius = OUTER_ORBIT if self.target_radius <= INNER_ORBIT else INNER_ORBIT

    # ------------------------------------------------------------ one frame

    def step(self, switch: bool = False, shield: bool = False) -> Events:
        """Advance one frame with the player's input and report what happened."""
        events = Events()
        if self.over:
            return events
        self.frame += 1
        self.shield = shield
        if switch:
            self.switch_orbit()

        self._move_ship()
        self.fuel = max(0.0, self.fuel - (FUEL_DRAIN_SHIELD if shield else FUEL_DRAIN))
        self._spawn()
        for ob in self.obstacles:
            ob.x += ob.vx
        self.obstacles = [ob for ob in self.obstacles if ob.x > OBSTACLE_REMOVE_X]
        self._collide(events)

        if self.fuel <= 0:
            events.out_of_fuel = True
        self.over = events.game_over
        return events

    def _move_ship(self) -> None:
        diff = self.target_radius - self.radius
        if abs(diff) > RADIUS_RATE:
            self.radius += math.copysign(RADIUS_RATE, diff)
        else:
            self.radius = self.target_radius
        self.angle += ANGULAR_SPEED

    def _spawn(self) -> None:
        if self.frame - self.last_obstacle_frame >= self.obstacle_interval():
            self.last_obstacle_frame = self.frame
            lo, hi = self.obstacle_speed_range()
            self.obstacles.append(Obstacle(
                x=self.rng.randint(*OBSTACLE_SPAWN_X),
                y=self.rng.randint(*OBSTACLE_SPAWN_Y),
                vx=-self.rng.uniform(lo, hi),
            ))
        if (self.frame - self.last_packet_frame >= PACKET_INTERVAL
                and len(self.packets) < MAX_PACKETS):
            self.last_packet_frame = self.frame
            r = self.rng.choice([INNER_ORBIT, OUTER_ORBIT])
            a = math.radians(self.rng.randint(0, 35) * 10)
            self.packets.append(Packet(r * math.cos(a), r * math.sin(a)))

    def _collide(self, events: Events) -> None:
        sx, sy = self.ship
        reach = SHIELD_RADIUS if self.shield else SHIP_RADIUS

        remaining = []
        for ob in self.obstacles:
            if math.hypot(sx - ob.x, sy - ob.y) < reach + OBSTACLE_RADIUS:
                if self.shield:
                    events.obstacles_destroyed += 1
                else:
                    events.crashed = True
            else:
                remaining.append(ob)
        self.obstacles = remaining

        remaining = []
        for p in self.packets:
            if math.hypot(sx - p.x, sy - p.y) < reach + PACKET_RADIUS:
                self.fuel = min(MAX_FUEL, self.fuel + PACKET_FUEL)
                events.packets_collected += 1
            else:
                remaining.append(p)
        self.packets = remaining
