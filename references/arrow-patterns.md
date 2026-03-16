# Arrow Connection Patterns

Reference for arrow routing in Python builder scripts. Read when building diagrams with 30+ elements.

---

## Single Continuous Arrows (No Gaps)

Every connection must be ONE continuous arrow from source to destination. Never use separate LINE + LINE + ARROW segments to simulate a junction -- they create visible gaps at connection points.

**Bad (gaps at junctions):**
```
LINE: box bottom >> junction Y
LINE: horizontal bar at junction
ARROW: junction center >> target
```

**Good (one piece per connection):**
```
ARROW: box bottom >> down >> sideways to center >> down >> target
```

---

## Merge Pattern (Many-to-One)

When multiple sources converge to one target, each source gets its own arrow with elbow points:

```python
# Left source: down, right to center, down to target
A("a_left", left_cx, src_bottom,
    [[0,0], [0, junction_dy], [mid_x - left_cx, junction_dy], [mid_x - left_cx, total_dy]])

# Center source: straight down
A("a_center", mid_x, src_bottom,
    [[0,0], [0, total_dy]])

# Right source: down, left to center, down to target
A("a_right", right_cx, src_bottom,
    [[0,0], [0, junction_dy], [mid_x - right_cx, junction_dy], [mid_x - right_cx, total_dy]])
```

---

## Split Pattern (One-to-Many)

Same approach reversed -- one arrow per target:

```python
# Hub to left target: down, left, down
A("a_to_left", mid_x, hub_bottom,
    [[0,0], [0, junction_dy], [left_cx - mid_x, junction_dy], [left_cx - mid_x, total_dy]])
```

---

## Data Store Connections

Database/storage boxes (Supabase, Notion, etc.) use dark fill (`#1e293b`) with white text. Arrows to/from data stores use elbow paths with the same patterns above.
