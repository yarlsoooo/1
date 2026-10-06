# -*- coding: utf-8 -*-
"""AIM 2627 Python Coursework —— 哨兵 Sentry 控制模块（学生骨架）。

你的全部作业都在本文件里：按题面（题面.pdf）各题的规范补全每个标有 TODO 的函数。
- 骨架已提供：Facing / SentryState 枚举、SentryGrid 的构造与只读属性、
  渲染函数 render_frame（demo 用，不进测试）。
- 你要实现：Q1-Q6 与 Bonus 的全部 TODO，以及 SentryGrid 的
  四个方法（current_pos 的 setter、move_forward、turn_left、turn_right）。
- 未实现的函数 raise NotImplementedError：可见测试会自动 skip，
  CI 一开始就是绿的；实现一个，对应测试亮一个。
- `python main.py`（或 PYTHONPATH=src python -m main）可看 ASCII 演示。
"""
import json
from collections import deque
from enum import Enum


# ---------------------------------------------------------------------------
# 仿真世界基础（已提供，勿改）
# ---------------------------------------------------------------------------
class Facing(Enum):
    """朝向枚举。世界坐标 (x, y)：x 向右增长，y 向上增长（数学系）。"""

    UP = (0, 1)
    DOWN = (0, -1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    @property
    def delta(self):
        """该朝向的单位位移向量 (dx, dy)。"""
        return self.value[0], self.value[1]


# ---------------------------------------------------------------------------
# Q1 机器人自检（题面 Q1·自检状态计算与报告生成）
# ---------------------------------------------------------------------------
def hp_ratio(hp, max_hp):
    """TODO(Q1)：血量百分比，返回 0-100 的 int；计算与边界规则见题面 Q1 规范。
    raise NotImplementedError("Q1 hp_ratio：题面 Q1·血量百分比与精度保障")
    """
    if max_hp <= 0:
        return 0
    return max(0, min(100, int((hp * 100 / max_hp))))


def status_report(name, robot_type, hp, max_hp, battery):
    """TODO(Q1)：一行自检报告字符串；档位判定与逐字符格式见题面 Q1 规范。
    raise NotImplementedError("Q1 status_report：题面 Q1·电量映射与报告格式")"""
    hp_percent = hp_ratio(hp, max_hp)
    battery_percent = max(0, min(100, int(battery)))
    if battery_percent < 20:
        battery_status = "LOW"
    elif battery_percent < 60:
        battery_status = "WARNING"
    else:
        battery_status = "OK"

    return (f"{name:<10}|{robot_type:^10}|HP {hp_percent:>3}%"
            f"|BAT {battery_percent:>3}%|{battery_status}")

# ---------------------------------------------------------------------------
# Q2 战斗日志分析（题面 Q2·多源日志解析与统计）
# ---------------------------------------------------------------------------


def analyze_damage_log(lines):
    """TODO(Q2)：解析混合格式伤害日志，返回固定契约的统计 dict；
    行格式、去重与统计口径见题面 Q2 规范。

    avg 按有效伤害项计算：每个传感器段和每条有效 JSON 记录各计一项。
    most_hit 出现并列时按 front、left、right 的顺序返回首个最大部位。
    若输入迭代器在读取期间抛出异常，停止读取并返回此前已解析的统计。
    raise NotImplementedError("Q2 analyze_damage_log：题面 Q2·多源日志解析与统计")"""
    # 初始化
    by_armor = {"front": 0, "left": 0, "right": 0}
    total = 0
    event_count = 0
    seen_ids = set()
    sensor_armor = {"F": "front", "L": "left", "R": "right"}

    try:
        iterator = iter(lines)
    except Exception:
        iterator = iter(())

    while True:
        try:
            raw_line = next(iterator)
        except StopIteration:
            break
        except Exception:
            break

        try:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            if line.startswith("{"):
                record = json.loads(line)
                if not isinstance(record, dict):
                    continue
                armor = record.get("armor")
                damage = record.get("damage")
                if (armor not in by_armor or type(damage) is not int
                        or damage <= 0):
                    continue
                if "id" in record:
                    id_key = json.dumps(record["id"], sort_keys=True,
                                        separators=(",", ":"))
                    if id_key in seen_ids:
                        continue
                    seen_ids.add(id_key)
                by_armor[armor] += damage
                total += damage
                event_count += 1
                continue

            segments = line.split(",")
            parsed = []
            valid = bool(segments)
            for segment in segments:
                pieces = segment.strip().split(":")
                if (len(pieces) != 2 or pieces[0].strip() not in sensor_armor
                        or not pieces[1].strip().isdigit()):
                    valid = False
                    break
                damage = int(pieces[1].strip())
                if damage <= 0:
                    valid = False
                    break
                parsed.append((sensor_armor[pieces[0].strip()], damage))
            if not valid:
                continue
            for armor, damage in parsed:
                by_armor[armor] += damage
                total += damage
                event_count += 1
        except Exception:
            # Malformed lines are ignored; one bad record must not abort parsing.
            continue

    most_hit = None
    if event_count:
        max_damage = max(by_armor.values())
        most_hit = next(armor for armor in ("front", "left", "right")
                        if by_armor[armor] == max_damage)
    average = round(total / event_count, 2) if event_count else 0.0
    return {"total": total, "by_armor": by_armor,
            "most_hit": most_hit, "avg": average}


# ---------------------------------------------------------------------------
# Q3 SentryGrid（题面 Q3·载体物理规则）
# ---------------------------------------------------------------------------
class SentryGrid:
    """哨兵仿真载体（构造与只读属性已提供；四个 TODO 方法由你实现）。"""

    def __init__(self, width, height, obstacles, enemy_pos,
                 start_pos=(0, 0), facing=Facing.UP, fuel=100):
        self._width = int(width)
        self._height = int(height)
        if self._width <= 0 or self._height <= 0:
            raise ValueError("地图尺寸必须为正")
        # 障碍坐标存入 set，查询 O(1)——已有实现，勿改。
        self._obstacles = set()
        for ob in obstacles:
            x, y = ob
            self._obstacles.add((int(x), int(y)))
        if not isinstance(enemy_pos, (tuple, list)) or len(enemy_pos) != 2:
            raise TypeError("enemy_pos 需要长度为 2 的 tuple/list")
        self._enemy_pos = self._clamp_cell(enemy_pos)
        if self._enemy_pos in self._obstacles:
            raise ValueError("enemy_pos 不能位于障碍物上")
        if not isinstance(facing, Facing):
            facing = Facing.UP
        self._facing = facing
        self._fuel = int(fuel)
        self._collision_count = 0
        self.current_pos = start_pos
        if self._pos in self._obstacles:
            raise ValueError("start_pos 不能位于障碍物上")

    def _clamp_cell(self, cell):
        """已提供：元素转 int 并夹回地图范围（供 __init__ 使用）。"""
        x = int(cell[0])
        y = int(cell[1])
        x = max(0, min(self._width - 1, x))
        y = max(0, min(self._height - 1, y))
        return (x, y)

    # -- 只读属性（已提供，勿改） ------------------------------------------
    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def enemy_pos(self):
        return self._enemy_pos

    @property
    def facing(self):
        return self._facing

    @property
    def fuel(self):
        return self._fuel

    @property
    def collision_count(self):
        return self._collision_count

    @property
    def obstacles(self):
        """障碍集合的只读视图（内部 set 引用，不要修改它）。"""
        return self._obstacles

    @property
    def found_enemy(self):
        return self._pos == self._enemy_pos

    def is_blocked(self, x, y):
        """已提供：坐标是否为障碍或越界（O(1)）。"""
        return ((x, y) in self._obstacles
                or not (0 <= x < self._width and 0 <= y < self._height))

    # -- 你要实现的部分 ------------------------------------------------------
    @property
    def current_pos(self):
        """当前位置 (x, y) 的 tuple。"""

        return self._pos

    @current_pos.setter
    def current_pos(self, value):
        """校验并设置当前位置，元素规范化后以 tuple 存储。"""
        if not isinstance(value, (tuple, list)) or len(value) != 2:
            raise TypeError("current_pos 需要长度为 2 的 tuple/list")
        try:
            self._pos = tuple(self._clamp_cell(value))
        except Exception:
            raise TypeError("current_pos 需要长度为 2 的 tuple/list")

    def move_forward(self):
        """TODO(Q3)：朝当前 facing 前进一格，返回执行后的位置；
        碰撞、耗电与断电语义见题面 Q3 规范。"""
        if self._fuel <= 0:
            return self._pos

        dx, dy = self._facing.delta
        next_x = self._pos[0] + dx
        next_y = self._pos[1] + dy
        if self.is_blocked(next_x, next_y):
            self._collision_count += 1
        else:
            self._pos = (next_x, next_y)
            self._fuel -= 1
        return self._pos

    def turn_left(self):
        """TODO(Q3)：原地左转 90°，返回新的 Facing（不耗电）。"""
        self._facing = {
            Facing.UP: Facing.LEFT,
            Facing.LEFT: Facing.DOWN,
            Facing.DOWN: Facing.RIGHT,
            Facing.RIGHT: Facing.UP,
        }[self._facing]
        return self._facing

    def turn_right(self):
        """TODO(Q3)：原地右转 90°，返回新的 Facing（不耗电）。"""
        self._facing = {
            Facing.UP: Facing.RIGHT,
            Facing.RIGHT: Facing.DOWN,
            Facing.DOWN: Facing.LEFT,
            Facing.LEFT: Facing.UP,
        }[self._facing]
        return self._facing


# ---------------------------------------------------------------------------
# Q4 贪心导航（题面 Q4·单步贪心导航策略）
# ---------------------------------------------------------------------------
def next_step_toward(pos, target, obstacles, current_facing=Facing.UP):
    """TODO(Q4)：返回下一步应朝向的 Facing；
    候选判定、优先级与回退规则见题面 Q4 规范。"""
    x, y = pos
    target_x, target_y = target
    dx = target_x - x
    dy = target_y - y

    candidates = {}
    if dx > 0:
        candidates["horizontal"] = (Facing.RIGHT, (x + 1, y))
    elif dx < 0:
        candidates["horizontal"] = (Facing.LEFT, (x - 1, y))
    if dy > 0:
        candidates["vertical"] = (Facing.UP, (x, y + 1))
    elif dy < 0:
        candidates["vertical"] = (Facing.DOWN, (x, y - 1))

    available = {
        axis: facing
        for axis, (facing, cell) in candidates.items()
        if cell not in obstacles
    }
    if not available:
        return current_facing

    preferred = "horizontal" if abs(dx) >= abs(dy) else "vertical"
    if preferred in available:
        return available[preferred]
    alternate = "vertical" if preferred == "horizontal" else "horizontal"
    return available[alternate]

# ---------------------------------------------------------------------------
# Q5 哨兵决策机（题面 Q5·裁判系统决策规则表）
# ---------------------------------------------------------------------------


class SentryState(Enum):
    """哨兵状态机（已提供，勿改）。"""

    PATROL = "PATROL"
    SUSPECT = "SUSPECT"
    ENGAGE = "ENGAGE"
    RETREAT = "RETREAT"
    RETURN = "RETURN"


def decide(sensor, state, hp, heat):
    """TODO(Q5)：纯函数决策，返回 (action: str, new_state: SentryState)；
    sensor 字段契约、R1-R7 规则表与非法输入处理见题面 Q5 规范。"""
    fields = ("enemy_frames", "enemy_dist", "robot_type", "max_hp")
    if not isinstance(sensor, dict) or any(key not in sensor for key in fields):
        raise ValueError("sensor 缺少必需字段")
    if not isinstance(state, SentryState):
        raise ValueError("非法哨兵状态")

    frames = sensor["enemy_frames"]
    if not isinstance(frames, (tuple, list)) or not 1 <= len(frames) <= 6:
        raise ValueError("enemy_frames 长度必须为 1 至 6")
    visible = bool(frames[-1])

    distance = sensor["enemy_dist"]
    # Invalid or unknown distance is treated as out of close-combat range.
    if type(distance) is not int or distance < 0:
        distance = float("inf")
    robot_type = sensor["robot_type"]
    if robot_type not in ("INFANTRY", "HERO"):
        robot_type = "INFANTRY"

    max_hp = sensor["max_hp"]
    if type(max_hp) is not int or max_hp <= 0:
        hp_pct = 0
    else:
        try:
            hp_pct = max(0, min(100, int(hp * 100 / max_hp)))
        except (TypeError, ValueError, OverflowError):
            hp_pct = 0

    # R1: low health takes precedence over all other rules.
    if hp_pct <= 30:
        return "RETREAT", SentryState.RETREAT

    # R2 and R3: retreat recovery and the one-frame return transition.
    if state is SentryState.RETREAT:
        return "RETURN", SentryState.RETURN
    if state is SentryState.RETURN:
        return "MOVE_BASE", SentryState.PATROL

    def engagement_action():
        if distance <= 3:
            return "SHOOT", SentryState.ENGAGE
        if robot_type == "HERO":
            return "MOVE_RIGHT", SentryState.ENGAGE
        return "MOVE_LEFT", SentryState.ENGAGE

    # R4 and R5: resolve an ongoing engagement.
    if state is SentryState.ENGAGE:
        if visible:
            return engagement_action()
        if len(frames) >= 2 and not bool(frames[-2]):
            return "SCAN", SentryState.SUSPECT
        return "HOLD_FIRE", SentryState.ENGAGE

    # R6: require two consecutive visible frames to engage.
    if visible:
        if len(frames) >= 2 and bool(frames[-2]):
            return engagement_action()
        return "SCAN", SentryState.SUSPECT

    # R7: state-specific behavior when no enemy is visible.
    if state is SentryState.PATROL:
        return "PATROL_MOVE", SentryState.PATROL
    return "SCAN", SentryState.SUSPECT

# ---------------------------------------------------------------------------
# Q6 巡逻任务（题面 Q6·巡逻契约与验收阈值）
# ---------------------------------------------------------------------------
def run_patrol(grid, max_steps=500):
    """Run the patrol loop, using a shortest-path step when greedy stalls."""
    steps = 0
    visited = {grid.current_pos}
    initial_collisions = grid.collision_count
    goal = grid.enemy_pos

    # Compute distance-to-goal for reachable cells. This is used only to
    # break greedy ties/detours and guarantees progress around obstacles.
    distances = {goal: 0}
    queue = [goal]
    index = 0
    while index < len(queue):
        x, y = queue[index]
        index += 1
        for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
            cell = (x + dx, y + dy)
            if cell not in distances and not grid.is_blocked(*cell):
                distances[cell] = distances[(x, y)] + 1
                queue.append(cell)

    directions = ((1, 0, Facing.RIGHT), (0, 1, Facing.UP),
                  (-1, 0, Facing.LEFT), (0, -1, Facing.DOWN))
    while (steps < max_steps and grid.fuel > 0
           and grid.current_pos != goal):
        # Sense carrier position/facing, then ask Q4 for the greedy direction.
        pos = grid.current_pos
        greedy = next_step_toward(pos, goal, grid.obstacles, grid.facing)
        gx, gy = greedy.delta
        greedy_cell = (pos[0] + gx, pos[1] + gy)
        distance = distances.get(pos)

        # A greedy step is accepted only when it is legal and advances along
        # a shortest route. Otherwise use the custom BFS escape direction.
        if (distance is not None and not grid.is_blocked(*greedy_cell)
                and distances.get(greedy_cell) == distance - 1):
            direction = greedy
        else:
            direction = None
            if distance is not None:
                for dx, dy, facing in directions:
                    cell = (pos[0] + dx, pos[1] + dy)
                    if distances.get(cell) == distance - 1:
                        direction = facing
                        break

        # For a disconnected target, explore legal unseen neighbors without
        # intentionally colliding; stop if the reachable area is exhausted.
        if direction is None:
            for dx, dy, facing in directions:
                cell = (pos[0] + dx, pos[1] + dy)
                if not grid.is_blocked(*cell) and cell not in visited:
                    direction = facing
                    break
            if direction is None:
                break

        while grid.facing is not direction:
            grid.turn_right()
        grid.move_forward()
        steps += 1
        visited.add(grid.current_pos)

    found = bool(grid.found_enemy)
    return {
        "steps": int(steps),
        "collisions": int(grid.collision_count - initial_collisions),
        "visited_count": int(len(visited)),
        "found_enemy": found,
        "success": found,
    }


def report_to_json(stats):
    return json.dumps(stats, sort_keys=True, separators=(",", ":"))


# ---------------------------------------------------------------------------
# Bonus：BFS 全局最短路（题面 Bonus·BFS 语义与排行榜）
# ---------------------------------------------------------------------------
def bfs_path_length(start, target, obstacles):
    """TODO(Bonus)：BFS 全局最短路步数；返回语义与边界职责见题面 Bonus 规范。"""
    if start == target:
        return 0
    blocked = set(obstacles)
    if start in blocked or target in blocked:
        return -1

    queue = deque([(start, 0)])
    visited = {start}
    while queue:
        current, distance = queue.popleft()
        x, y = current
        for neighbor in ((x + 1, y), (x - 1, y),
                         (x, y + 1), (x, y - 1)):
            if neighbor in blocked or neighbor in visited:
                continue
            if neighbor == target:
                return distance + 1
            visited.add(neighbor)
            queue.append((neighbor, distance + 1))
    return -1


# ---------------------------------------------------------------------------
# 渲染（已提供，demo 专用，不进测试）
# ---------------------------------------------------------------------------
def render_frame(grid, trail=()):
    """ASCII 渲染一帧战场；trail 为走过的格子集合。返回 list[str]。"""
    trail = set(trail)
    rows = []
    for y in range(grid.height - 1, -1, -1):
        row = []
        for x in range(grid.width):
            if (x, y) == grid.current_pos:
                row.append("◉")
            elif (x, y) == grid.enemy_pos:
                row.append("▲")
            elif (x, y) in grid.obstacles:
                row.append("█")
            elif (x, y) in trail:
                row.append("·")
            else:
                row.append(".")
        rows.append("".join(row))
    return rows
