"""
database.py  SQLite persistence layer for Karesabari.

Tables:
  - plants          : user garden plants with scheduling metadata
  - watering_log    : watering history per plant
  - weekly_checkins : growth check-in entries
  - messages        : water-request relay messages
  - catalogue       : vegetable reference data
  - event_log       : app-wide activity log for dev panel
"""

from __future__ import annotations

import os
import sqlite3
import threading
import functools
import random
from datetime import datetime, timedelta
from typing import Optional


DB_PATH = os.path.join(os.path.dirname(__file__), "karesabari.db")

_connect_lock = threading.Lock()

_current_user: Optional[dict] = None
_last_auth_error: str = ""


# Handle connect
def _connect() -> sqlite3.Connection:
    """Create a SQLite connection with Row mapping and basic thread safety."""
    with _connect_lock:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
        except Exception:
            pass
        return conn


# Update current user
def set_current_user(user: Optional[dict]) -> None:
    """Set the currently logged-in user."""
    global _current_user
    _current_user = user
    try:
        _invalidate_caches()
    except Exception:
        pass


# Return current user
def get_current_user() -> Optional[dict]:
    """Get the currently logged-in user."""
    return _current_user


# Return current garden id
def get_current_garden_id() -> Optional[str]:
    """Get the garden_id of the currently logged-in user."""
    if _current_user:
        gid = _current_user.get("garden_id")
        if gid:
            return str(gid)
        fid = _current_user.get("family_id")
        if fid is not None:
            return str(fid)
    return None


# Return current garden row id
def get_current_garden_row_id() -> Optional[int]:
    """Return gardens.id for the current garden_id (if resolvable)."""
    gid = get_current_garden_id()
    if not gid:
        return None
    conn = _connect()
    try:
        r = conn.execute("SELECT id FROM gardens WHERE garden_id = ?", (gid,)).fetchone()
        return int(r["id"]) if r else None
    finally:
        conn.close()


# Return current user id
def get_current_user_id() -> Optional[int]:
    if _current_user and _current_user.get("id") is not None:
        try:
            return int(_current_user["id"])
        except Exception:
            return None
    return None


# Return current family id
def get_current_family_id() -> Optional[int]:
    """Compatibility helper for legacy callers that still use family_id."""
    if _current_user and _current_user.get("family_id") is not None:
        try:
            return int(_current_user["family_id"])
        except Exception:
            return None
    return None



# Handle now iso
def _now_iso() -> str:
    return datetime.now().isoformat()


# Generate garden id
def generate_garden_id() -> str:
    """Generate a unique 6-digit Garden ID as a string."""
    for _ in range(50):
        gid = f"{random.randint(0, 999999):06d}"
        try:
            if not garden_exists(gid):
                return gid
        except Exception:
            return gid
    return f"{random.randint(0, 999999):06d}"


# Handle garden exists
def garden_exists(garden_id: str) -> bool:
    conn = _connect()
    try:
        row = conn.execute("SELECT 1 FROM gardens WHERE garden_id = ?", (str(garden_id),)).fetchone()
        return row is not None
    finally:
        conn.close()



# Handle init db
def init_db() -> None:
    """Create tables if they don't exist and seed catalogue data."""
    conn = _connect()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS gardens (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            garden_id       TEXT UNIQUE NOT NULL,
            name            TEXT NOT NULL,
            created_at      TEXT NOT NULL
        );

        -- Keep families for backward compatibility with older installs
        CREATE TABLE IF NOT EXISTS families (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL,
            created_at      TEXT NOT NULL
        );

        -- Map legacy family ids to new 6-digit garden ids
        CREATE TABLE IF NOT EXISTS family_garden_map (
            family_id   INTEGER PRIMARY KEY,
            garden_id   TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS users (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            username        TEXT UNIQUE NOT NULL,
            password        TEXT NOT NULL,
            family_id       INTEGER,
            garden_id       TEXT,
            created_at      TEXT NOT NULL,
            theme_pref      TEXT DEFAULT 'light',
            FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS plants (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL,
            name_nepali     TEXT DEFAULT '',
            scientific_name TEXT DEFAULT '',
            status          TEXT DEFAULT 'healthy',
            water_freq_hours REAL DEFAULT 24,
            planted_on      TEXT,
            notes           TEXT DEFAULT '',
            season          TEXT DEFAULT '',
            soil_type       TEXT DEFAULT '',
            water_need      TEXT DEFAULT 'medium',
            streak          INTEGER DEFAULT 0,
            longest_streak  INTEGER DEFAULT 0,
            total_waterings INTEGER DEFAULT 0,
            last_watered_at TEXT,
            next_water_at   TEXT,
            family_id       INTEGER,
            garden_id       TEXT,
            image_path      TEXT DEFAULT '',
            FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS watering_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            plant_id   INTEGER NOT NULL,
            watered_at TEXT NOT NULL,
            on_time    INTEGER DEFAULT 1,
            FOREIGN KEY (plant_id) REFERENCES plants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS weekly_checkins (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            plant_id    INTEGER NOT NULL,
            week_date   TEXT NOT NULL,
            height_cm   REAL,
            new_leaves  INTEGER DEFAULT 0,
            flowering   INTEGER DEFAULT 0,
            note        TEXT DEFAULT '',
            image_path  TEXT DEFAULT '',
            FOREIGN KEY (plant_id) REFERENCES plants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS messages (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            sender     TEXT DEFAULT 'System',
            content    TEXT NOT NULL,
            msg_type   TEXT DEFAULT 'info',
            created_at TEXT NOT NULL,
            user_id    INTEGER,
            family_id  INTEGER,
            garden_id  TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS catalogue (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT UNIQUE NOT NULL,
            name_nepali  TEXT,
            scientific_name TEXT DEFAULT '',
            season       TEXT,
            water_need   TEXT DEFAULT 'medium',
            soil_type    TEXT DEFAULT 'loamy',
            description  TEXT DEFAULT '',
            water_freq_hours REAL DEFAULT 24,
            difficulty   TEXT DEFAULT 'easy',
            image_path   TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS event_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp  TEXT NOT NULL,
            event_type TEXT NOT NULL,
            details    TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS garden_invites (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            garden_id         TEXT NOT NULL,
            invited_username  TEXT NOT NULL,
            invited_user_id   INTEGER,
            invited_by_user_id INTEGER,
            status            TEXT NOT NULL DEFAULT 'pending',
            created_at        TEXT NOT NULL,
            responded_at      TEXT,
            FOREIGN KEY (invited_user_id) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (invited_by_user_id) REFERENCES users(id) ON DELETE SET NULL
        );
    """)

    user_cols = [r[1] for r in cur.execute("PRAGMA table_info(users)").fetchall()]
    if "garden_id" not in user_cols:
        cur.execute("ALTER TABLE users ADD COLUMN garden_id TEXT")

    plant_cols = [r[1] for r in cur.execute("PRAGMA table_info(plants)").fetchall()]
    if "garden_id" not in plant_cols:
        cur.execute("ALTER TABLE plants ADD COLUMN garden_id TEXT")

    if "image_path" not in plant_cols:
        cur.execute("ALTER TABLE plants ADD COLUMN image_path TEXT DEFAULT ''")
    if "scientific_name" not in plant_cols:
        cur.execute("ALTER TABLE plants ADD COLUMN scientific_name TEXT DEFAULT ''")

    weekly_cols = [r[1] for r in cur.execute("PRAGMA table_info(weekly_checkins)").fetchall()]
    if "image_path" not in weekly_cols:
        cur.execute("ALTER TABLE weekly_checkins ADD COLUMN image_path TEXT DEFAULT ''")
    cur.execute("DROP INDEX IF EXISTS idx_weekly_checkins_plant_week")

    msg_cols = [r[1] for r in cur.execute("PRAGMA table_info(messages)").fetchall()]
    if "garden_id" not in msg_cols:
        cur.execute("ALTER TABLE messages ADD COLUMN garden_id TEXT")

    if "user_id" not in msg_cols:
        cur.execute("ALTER TABLE messages ADD COLUMN user_id INTEGER")
    if "family_id" not in msg_cols:
        cur.execute("ALTER TABLE messages ADD COLUMN family_id INTEGER")

    cols = [r[1] for r in cur.execute("PRAGMA table_info(catalogue)").fetchall()]
    if "image_path" not in cols:
        cur.execute("ALTER TABLE catalogue ADD COLUMN image_path TEXT DEFAULT ''")
    if "scientific_name" not in cols:
        cur.execute("ALTER TABLE catalogue ADD COLUMN scientific_name TEXT DEFAULT ''")

    try:
        fam_rows = cur.execute("SELECT id, name, created_at FROM families").fetchall()
        for r in fam_rows:
            fid = int(r["id"])
            mapped = cur.execute("SELECT garden_id FROM family_garden_map WHERE family_id = ?", (fid,)).fetchone()
            if mapped and mapped["garden_id"]:
                gid = str(mapped["garden_id"])
            else:
                gid = generate_garden_id()
                cur.execute(
                    "INSERT OR REPLACE INTO family_garden_map (family_id, garden_id) VALUES (?, ?)",
                    (fid, gid),
                )

            exists = cur.execute("SELECT 1 FROM gardens WHERE garden_id = ?", (gid,)).fetchone()
            if not exists:
                cur.execute(
                    "INSERT INTO gardens (garden_id, name, created_at) VALUES (?, ?, ?)",
                    (gid, r["name"], r["created_at"]),
                )

        cur.execute(
            """
            UPDATE users
               SET garden_id = (
                   SELECT m.garden_id FROM family_garden_map m WHERE m.family_id = users.family_id
               )
             WHERE (garden_id IS NULL OR garden_id = '' OR LENGTH(garden_id) != 6 OR garden_id GLOB '*[^0-9]*')
               AND family_id IS NOT NULL
            """
        )

        cur.execute(
            """
            UPDATE plants
               SET garden_id = (
                   SELECT m.garden_id FROM family_garden_map m WHERE m.family_id = plants.family_id
               )
             WHERE (garden_id IS NULL OR garden_id = '' OR LENGTH(garden_id) != 6 OR garden_id GLOB '*[^0-9]*')
               AND family_id IS NOT NULL
            """
        )

        cur.execute(
            """
            UPDATE messages
               SET garden_id = (
                   SELECT m.garden_id FROM family_garden_map m WHERE m.family_id = messages.family_id
               )
             WHERE (garden_id IS NULL OR garden_id = '' OR LENGTH(garden_id) != 6 OR garden_id GLOB '*[^0-9]*')
               AND family_id IS NOT NULL
            """
        )

        rows = cur.execute("SELECT DISTINCT garden_id FROM users WHERE garden_id IS NOT NULL AND garden_id != ''").fetchall()
        for rr in rows:
            gid = str(rr["garden_id"])
            if not (gid.isdigit() and len(gid) == 6):
                continue
            exists = cur.execute("SELECT 1 FROM gardens WHERE garden_id = ?", (gid,)).fetchone()
            if not exists:
                cur.execute(
                    "INSERT INTO gardens (garden_id, name, created_at) VALUES (?, ?, ?)",
                    (gid, "Garden", _now_iso()),
                )

    except Exception:
        pass

    if cur.execute("SELECT COUNT(*) FROM catalogue").fetchone()[0] == 0:
        _seed_catalogue(cur)

    if cur.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        _seed_users(cur)

        cur.execute(
                """
                UPDATE plants
                     SET scientific_name = (
                             SELECT c.scientific_name
                                 FROM catalogue c
                                WHERE lower(trim(c.name)) = lower(trim(plants.name))
                                LIMIT 1
                     )
                 WHERE (scientific_name IS NULL OR trim(scientific_name) = '')
                     AND EXISTS (
                             SELECT 1
                                 FROM catalogue c
                                WHERE lower(trim(c.name)) = lower(trim(plants.name))
                                    AND trim(coalesce(c.scientific_name, '')) <> ''
                     )
                """
        )

    conn.commit()

    cur.execute("CREATE INDEX IF NOT EXISTS idx_plants_garden_id ON plants(garden_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_garden_id ON messages(garden_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_users_garden_id ON users(garden_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_plants_family ON plants(family_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_plants_next ON plants(next_water_at);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_watering_plant ON watering_log(plant_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_user_family ON messages(user_id, family_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_catalogue_name ON catalogue(name);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_invites_user_status ON garden_invites(invited_username, status);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_invites_garden_status ON garden_invites(garden_id, status);")
    conn.commit()
    conn.close()


# Handle invalidate caches
def _invalidate_caches():
    _cached_get_all_plants.cache_clear()
    _cached_search_catalogue.cache_clear()
    _cached_get_catalogue_item.cache_clear()
    _cached_get_messages.cache_clear()
    try:
        _cached_get_garden_members.cache_clear()
        _cached_get_user_gardens.cache_clear()
    except Exception:
        pass
    try:
        _cached_get_pending_invites.cache_clear()
    except Exception:
        pass


# Seed catalogue
def _seed_catalogue(cur: sqlite3.Cursor) -> None:
    """Seed with common and expanded Nepali kitchen-garden vegetables."""
    vegetables = [
        ("Tomato", "गोलभेदा", "Solanum lycopersicum", "Summer", "high", "loamy", "Staple in every Nepali kitchen. Needs full sun.", 12, "easy", ""),
        ("Rayo ko Saag", "रायो", "Brassica juncea", "Winter", "medium", "loamy", "Mustard greens, perfect for Gundruk preparation.", 24, "easy", ""),
        ("Cauliflower", "काउली", "Brassica oleracea var. botrytis", "Winter", "medium", "clay-loam", "Grows well in cooler hill climates.", 24, "medium", ""),
        ("Spinach", "पालुन्गो", "Spinacia oleracea", "Winter", "medium", "sandy-loam", "Quick-growing leafy green rich in iron.", 24, "easy", ""),
        ("Chili", "खुर्सानी", "Capsicum annuum", "Summer", "low", "well-drained", "Essential spice crop. Drought tolerant once established.", 48, "easy", ""),
        ("Cucumber", "काक्रो", "Cucumis sativus", "Summer", "high", "sandy-loam", "Refreshing summer crop. Needs regular watering.", 12, "easy", ""),
        ("Bitter Gourd", "तिते करेला", "Momordica charantia", "Summer", "medium", "loamy", "Medicinal value. Common in Terai gardens.", 24, "medium", ""),
        ("Pumpkin", "फर्सी", "Cucurbita moschata", "Monsoon", "medium", "rich-loam", "Versatile crop. Leaves and fruit both edible.", 36, "easy", ""),
        ("Radish", "मुला", "Raphanus sativus", "Winter", "medium", "deep-loam", "Fast grower. Ideal for beginners.", 24, "easy", ""),
        ("Beans", "सिमी", "Phaseolus vulgaris", "Monsoon", "medium", "loamy", "Climbing variety. Fixes nitrogen in soil.", 24, "medium", ""),
        ("Potato", "आलु", "Solanum tuberosum", "Winter", "medium", "sandy-loam", "Staple crop. Grows well in hills.", 48, "easy", ""),
        ("Onion", "प्याज", "Allium cepa", "Winter", "low", "well-drained", "Long storage life. Essential kitchen ingredient.", 72, "medium", ""),
        ("Garlic", "लसुन", "Allium sativum", "Winter", "low", "well-drained", "Medicinal and culinary uses.", 72, "easy", ""),
        ("Coriander", "धनिया", "Coriandrum sativum", "Winter", "low", "loamy", "Quick herb. Used fresh in every meal.", 24, "easy", ""),
        ("Okra", "भिन्दी", "Abelmoschus esculentus", "Summer", "medium", "loamy", "Heat-loving crop. Popular in Terai.", 24, "medium", ""),
        ("Eggplant", "भान्टा", "Solanum melongena", "Summer", "medium", "sandy-loam", "Known as Brinjal. Comes in various shapes and sizes.", 24, "medium", ""),
        ("Bottle Gourd", "लौका", "Lagenaria siceraria", "Summer", "high", "loamy", "Climbing vine. Great for summer stews.", 18, "easy", ""),
        ("Sponge Gourd", "घिरौला", "Luffa aegyptiaca", "Summer", "medium", "loamy", "Commonly used in Nepali curries.", 24, "easy", ""),
        ("Snake Gourd", "चिचिण्डो", "Trichosanthes cucumerina", "Summer", "medium", "loamy", "Long, slender gourd with distinct stripes.", 24, "medium", ""),
        ("Garden Pea", "केराउ", "Pisum sativum", "Winter", "medium", "well-drained", "Fresh sweet peas for winter snacks.", 24, "medium", ""),
        ("Broad Bean", "बकुल्ला", "Vicia faba", "Winter", "medium", "heavy-loam", "Nutritious beans, common in traditional dishes.", 36, "medium", ""),
        ("Cabbage", "बन्दा गोभी", "Brassica oleracea var. capitata", "Winter", "high", "clay-loam", "Crunchy leaves, essential for chowmein and curries.", 24, "medium", ""),
        ("Broccoli", "ब्रोकाउली", "Brassica oleracea var. italica", "Winter", "medium", "loamy", "Superfood that thrives in cold Nepali winters.", 24, "medium", ""),
        ("Chayote", "इस्कुस", "Sechium edule", "Monsoon", "medium", "loamy", "Vigorous climber. Roots and fruits are edible.", 48, "easy", ""),
        ("Ginger", "अदुवा", "Zingiber officinale", "Monsoon", "high", "sandy-loam", "Grows underground. Essential for tea and cooking.", 48, "medium", ""),
        ("Turmeric", "बेसार", "Curcuma longa", "Monsoon", "high", "loamy", "Powerful medicinal properties. Harvest after leaves dry.", 48, "medium", ""),
        ("Fenugreek", "मेथी", "Trigonella foenum-graecum", "Winter", "low", "loamy", "Used as a leafy green (Methi ko Saag) or spice.", 24, "easy", ""),
        ("Broad Leaf Mustard", "चम्सुर", "Lepidium sativum", "Winter", "medium", "loamy", "Often paired with Palungo in Nepali salads.", 24, "easy", ""),
        ("Swiss Chard", "स्विस चार्ड", "Beta vulgaris subsp. vulgaris", "Winter", "medium", "loamy", "Resilient leafy green with colorful stalks.", 24, "easy", ""),
        ("Turnip", "फर्सी मुला", "Brassica rapa subsp. rapa", "Winter", "medium", "sandy-loam", "Both the bulb and leaves are edible.", 24, "medium", ""),
        ("Carrot", "गाजर", "Daucus carota", "Winter", "medium", "sandy-loose", "Needs deep, loose soil to grow straight.", 36, "medium", ""),
        ("Sweet Potato", "सखरखण्ड", "Ipomoea batatas", "Summer", "low", "sandy-loam", "Trailing vine with sweet tuberous roots.", 48, "easy", ""),
        ("Yam", "तरुल", "Dioscorea", "Monsoon", "medium", "well-drained", "Traditional root vegetable for Maghe Sankranti.", 72, "hard", ""),
        ("Pointed Gourd", "परवल", "Trichosanthes dioica", "Summer", "medium", "sandy-loam", "Popular in the Terai plains of Nepal.", 24, "medium", ""),
        ("Asparagus", "कुरिलो", "Asparagus officinalis", "Spring", "high", "well-drained", "High-value crop. Needs patience to establish.", 24, "hard", ""),
    ]
    cur.executemany(
        "INSERT INTO catalogue (name, name_nepali, scientific_name, season, water_need, soil_type, description, water_freq_hours, difficulty, image_path) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        vegetables,
    )



# Handle cached get all plants
@functools.lru_cache(maxsize=128)
def _cached_get_all_plants(garden_id: Optional[str]):
    conn = _connect()
    try:
        if garden_id:
            rows = conn.execute(
                "SELECT * FROM plants WHERE garden_id = ? ORDER BY id DESC",
                (str(garden_id),),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM plants ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# Handle cached search catalogue
@functools.lru_cache(maxsize=256)
def _cached_search_catalogue(query: str):
    conn = _connect()
    try:
        q = (query or "").strip()
        if not q:
            rows = conn.execute("SELECT * FROM catalogue ORDER BY name").fetchall()
            return [dict(r) for r in rows]
        like = f"%{q}%"
        rows = conn.execute(
            "SELECT * FROM catalogue WHERE name LIKE ? OR name_nepali LIKE ? OR season LIKE ? OR scientific_name LIKE ? ORDER BY name",
            (like, like, like, like),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# Handle cached get catalogue item
@functools.lru_cache(maxsize=512)
def _cached_get_catalogue_item(item_id: int):
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM catalogue WHERE id = ?", (item_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# Handle cached get messages
@functools.lru_cache(maxsize=32)
def _cached_get_messages(garden_id: Optional[str], user_id: Optional[int], limit: int = 50):
    conn = _connect()
    try:
        params = []
        where = []
        if user_id is not None:
            where.append("user_id = ?")
            params.append(int(user_id))
        if garden_id:
            where.append("garden_id = ?")
            params.append(str(garden_id))
        if not where:
            return []
        sql = f"SELECT * FROM messages WHERE ({' OR '.join(where)}) ORDER BY id DESC LIMIT ?"
        params.append(int(limit))
        rows = conn.execute(sql, tuple(params)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# Handle cached get garden members
@functools.lru_cache(maxsize=64)
def _cached_get_garden_members(garden_id: str) -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, username, garden_id, created_at, theme_pref FROM users WHERE garden_id = ? ORDER BY id",
            (str(garden_id),),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# Handle cached get user gardens
@functools.lru_cache(maxsize=64)
def _cached_get_user_gardens(user_id: int) -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT DISTINCT garden_id FROM users WHERE id = ?",
            (int(user_id),),
        ).fetchall()
        gids = [str(r["garden_id"]) for r in rows if r.get("garden_id")]
        out: list[dict] = []
        for gid in gids:
            g = conn.execute("SELECT garden_id, name, created_at FROM gardens WHERE garden_id = ?", (gid,)).fetchone()
            if g:
                out.append(dict(g))
            else:
                out.append({"garden_id": gid, "name": "(Unknown)", "created_at": ""})
        return out
    finally:
        conn.close()


# Seed users
def _seed_users(cur: sqlite3.Cursor) -> None:
    now = _now_iso()
    demo_gid = "000001"
    cur.execute(
        "INSERT OR IGNORE INTO gardens (garden_id, name, created_at) VALUES (?, ?, ?)",
        (demo_gid, "Demo Garden", now),
    )

    cur.execute("INSERT INTO families (name, created_at) VALUES (?, ?)", ("Family", now))
    family1_id = cur.lastrowid
    cur.execute("INSERT INTO families (name, created_at) VALUES (?, ?)", ("Lone Gardener", now))
    family2_id = cur.lastrowid

    users = [
        ("dad", "dad123", family1_id, demo_gid),
        ("mom", "mom123", family1_id, demo_gid),
        ("kid", "kid123", family1_id, demo_gid),
        ("john", "john123", family2_id, demo_gid),
    ]
    for username, password, family_id, garden_id in users:
        cur.execute(
            "INSERT OR IGNORE INTO users (username, password, family_id, garden_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (username, password, family_id, garden_id, now),
        )


# Create garden
def create_garden(name: str = "My Garden") -> dict:
    """Create a new garden and return its row."""
    gid = generate_garden_id()
    now = _now_iso()
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO gardens (garden_id, name, created_at) VALUES (?, ?, ?)",
            (gid, name or "My Garden", now),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM gardens WHERE garden_id = ?", (gid,)).fetchone()
        return dict(row) if row else {"garden_id": gid, "name": name, "created_at": now}
    finally:
        conn.close()


# Normalize username
def _normalize_username(username: str) -> str:
    return (username or "").strip().lower()


# Handle users family id required
def _users_family_id_required(conn: sqlite3.Connection) -> bool:
    """Return True when legacy schema enforces users.family_id as NOT NULL."""
    try:
        cols = conn.execute("PRAGMA table_info(users)").fetchall()
        for c in cols:
            if str(c[1]) == "family_id":
                return bool(c[3])
    except Exception:
        pass
    return False


# Ensure legacy family for garden
def _ensure_legacy_family_for_garden(
    conn: sqlite3.Connection,
    garden_id: str,
    garden_name: str = "Garden",
) -> Optional[int]:
    """Ensure a legacy families.id exists and is mapped to garden_id."""
    gid = str(garden_id or "").strip()
    if not gid:
        return None

    row = conn.execute(
        "SELECT family_id FROM family_garden_map WHERE garden_id = ? LIMIT 1",
        (gid,),
    ).fetchone()
    if row and row["family_id"] is not None:
        try:
            return int(row["family_id"])
        except Exception:
            pass

    now = _now_iso()
    cur = conn.execute(
        "INSERT INTO families (name, created_at) VALUES (?, ?)",
        (garden_name or "Garden", now),
    )
    fid = int(cur.lastrowid)
    conn.execute(
        "INSERT OR REPLACE INTO family_garden_map (family_id, garden_id) VALUES (?, ?)",
        (fid, gid),
    )
    return fid


# Create user
def create_user(
    username: str,
    password: str,
    garden_name: str = "My Garden",
    garden_id: Optional[str] = None,
    invite_id: Optional[int] = None,
) -> Optional[dict]:
    """Create a new user.

    If garden_id is provided, the user joins that existing garden.
    Otherwise, a new garden is created with a unique 6-digit garden_id.

    Returns the created user row as a dict, or None on failure.
    """
    now = _now_iso()
    global _last_auth_error
    _last_auth_error = ""
    u_raw = (username or "").strip()
    u = _normalize_username(username)
    p = (password or "").strip()
    if not u or not p:
        return None

    try:
        init_db()
    except Exception:
        pass

    try:
        conn_chk = _connect()
        row = conn_chk.execute(
            "SELECT id FROM users WHERE lower(trim(username)) = ? LIMIT 1",
            (u,),
        ).fetchone()
        conn_chk.close()
        if row:
            return None
    except Exception:
        pass

    gid: Optional[str] = None
    invite_row = None
    if invite_id is not None:
        try:
            conn_inv = _connect()
            invite_row = conn_inv.execute(
                "SELECT id, garden_id, invited_username, status FROM garden_invites WHERE id = ? LIMIT 1",
                (int(invite_id),),
            ).fetchone()
            conn_inv.close()
        except Exception:
            invite_row = None
        if not invite_row:
            _last_auth_error = "Invite not found"
            return None
        if str(invite_row["status"] or "") != "pending":
            _last_auth_error = "Invite is no longer pending"
            return None
        invited_username = _normalize_username(str(invite_row["invited_username"] or ""))
        if invited_username and invited_username != u:
            _last_auth_error = "Invite does not match this username"
            return None
        gid = str(invite_row["garden_id"] or "").strip()
        if not (gid.isdigit() and len(gid) == 6 and garden_exists(gid)):
            _last_auth_error = "Invite garden not found"
            return None

    elif garden_id:
        gid = str(garden_id).strip()
        if not (gid.isdigit() and len(gid) == 6):
            return None
        if not garden_exists(gid):
            return None
    else:
        garden = create_garden(name=(garden_name or "My Garden").strip() or "My Garden")
        gid = str(garden.get("garden_id")) if garden else None
        if not gid:
            return None

    conn = _connect()
    try:
        cur = conn.cursor()
        legacy_family_id = None
        if _users_family_id_required(conn):
            legacy_family_id = _ensure_legacy_family_for_garden(
                conn,
                gid,
                garden_name or "My Garden",
            )
            if legacy_family_id is None:
                _last_auth_error = "Legacy schema requires family_id, but none could be resolved"
                return None

        cur.execute(
            "INSERT INTO users (username, password, family_id, garden_id, created_at, theme_pref) VALUES (?, ?, ?, ?, ?, ?)",
            (u, p, legacy_family_id, gid, now, "light"),
        )
        conn.commit()

        user_id = cur.lastrowid
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        user = dict(row) if row else None
        if user is None:
            user = {"id": user_id, "username": u, "garden_id": gid, "theme_pref": "light"}

        if invite_row is not None:
            conn.execute(
                "UPDATE garden_invites SET status = 'accepted', invited_user_id = ?, responded_at = ? WHERE id = ?",
                (user_id, _now_iso(), int(invite_row["id"])),
            )
            conn.execute(
                "INSERT INTO messages (sender, content, msg_type, created_at, garden_id) VALUES (?, ?, ?, ?, ?)",
                (
                    "Garden Invite",
                    f"{user.get('username', 'A user')} joined via invite.",
                    "success",
                    _now_iso(),
                    gid,
                ),
            )
            conn.commit()

        set_current_user(user)
        return user

    except sqlite3.IntegrityError as e:
        try:
            conn.rollback()
        except Exception:
            pass
        _last_auth_error = f"IntegrityError: {e}"
        return None

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        _last_auth_error = f"CreateUserError: {e}"
        return None

    finally:
        try:
            conn.close()
        except Exception:
            pass
        _invalidate_caches()


# Return last auth error
def get_last_auth_error() -> str:
    """Return last user/auth related error message (best-effort)."""
    try:
        return str(globals().get("_last_auth_error") or "")
    except Exception:
        return ""


# Authenticate the current data
def authenticate(username: str, password: str) -> tuple[bool, str, Optional[dict]]:
    global _last_auth_error
    _last_auth_error = ""
    if not username or not password:
        return False, "Enter username and password", None
    u = _normalize_username(username)
    p = (password or "").strip()
    if not u or not p:
        return False, "Enter username and password", None

    conn = _connect()
    try:
        user = conn.execute(
            "SELECT id, username, family_id, garden_id, theme_pref "
            "FROM users WHERE lower(trim(username)) = ? AND password = ?",
            (u, p),
        ).fetchone()
        if user:
            return True, "OK", dict(user)
        _last_auth_error = "Invalid credentials"
        return False, "Invalid credentials", None
    finally:
        conn.close()



# Add plant
def add_plant(
    name: str,
    name_nepali: str = "",
    scientific_name: str = "",
    water_freq_hours: float = 24,
    notes: str = "",
    season: str = "",
    soil_type: str = "",
    water_need: str = "medium",
    family_id: Optional[int] = None,
    image_path: str = "",
) -> int:
    if isinstance(name, dict):
        data = name
        name = str(data.get("name") or "").strip()
        name_nepali = str(data.get("name_nepali") or "").strip()
        scientific_name = str(data.get("scientific_name") or "").strip()
        notes = str(data.get("notes") or "").strip()
        season = str(data.get("season") or "").strip()
        soil_type = str(data.get("soil_type") or "").strip()
        image_path = str(data.get("image_path") or "").strip()

        water_need_raw = str(data.get("water_need") or data.get("water_needed") or "medium").strip().lower()
        water_need = water_need_raw if water_need_raw in {"low", "medium", "high"} else "medium"

        if data.get("water_freq_hours") is not None:
            try:
                water_freq_hours = float(data.get("water_freq_hours"))
            except Exception:
                water_freq_hours = 24
        elif data.get("watering_interval_days") is not None:
            try:
                water_freq_hours = max(1.0, float(data.get("watering_interval_days")) * 24)
            except Exception:
                water_freq_hours = 24

    if not str(name).strip():
        raise ValueError("Plant name is required")

    now = _now_iso()
    next_water = (datetime.now() + timedelta(hours=water_freq_hours)).isoformat()

    sci = (scientific_name or "").strip()
    if not sci:
        conn_lookup = _connect()
        try:
            rr = conn_lookup.execute(
                "SELECT scientific_name FROM catalogue WHERE lower(trim(name)) = lower(trim(?)) LIMIT 1",
                (name,),
            ).fetchone()
            if rr and str(rr["scientific_name"] or "").strip():
                sci = str(rr["scientific_name"] or "").strip()
        finally:
            conn_lookup.close()

    garden_id = get_current_garden_id()

    conn = _connect()
    cur = conn.execute(
        "INSERT INTO plants (name, name_nepali, scientific_name, water_freq_hours, planted_on, notes, "
        "season, soil_type, water_need, last_watered_at, next_water_at, family_id, garden_id, image_path) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            name,
            name_nepali,
            sci,
            water_freq_hours,
            now,
            notes,
            season,
            soil_type,
            water_need,
            now,
            next_water,
            family_id,
            garden_id,
            image_path,
        ),
    )
    conn.commit()
    pid = cur.lastrowid
    conn.close()
    _invalidate_caches()
    log_event("plant_added", f"Plant '{name}' (id={pid}) added to garden")
    return pid


# Add plant from catalogue
def add_plant_from_catalogue(catalogue_id: int, notes: str = "") -> Optional[int]:
    item = get_catalogue_item(catalogue_id)
    if not item:
        return None
    return add_plant(
        name=item["name"],
        name_nepali=item.get("name_nepali", ""),
        scientific_name=item.get("scientific_name", ""),
        water_freq_hours=item.get("water_freq_hours", 24),
        notes=notes,
        season=item.get("season", ""),
        soil_type=item.get("soil_type", ""),
        water_need=item.get("water_need", "medium"),
        image_path=item.get("image_path", "") or "",    # <-- added
    )


# Return all plants
def get_all_plants() -> list[dict]:
    return _cached_get_all_plants(get_current_garden_id())


# Return plant
def get_plant(plant_id: int) -> Optional[dict]:
    conn = _connect()
    row = conn.execute("SELECT * FROM plants WHERE id = ?", (plant_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# Delete plant now
def delete_plant(plant_id: int) -> None:
    plant = get_plant(plant_id)
    conn = _connect()
    conn.execute("DELETE FROM plants WHERE id = ?", (plant_id,))
    conn.commit()
    conn.close()
    _invalidate_caches()
    name = plant["name"] if plant else f"#{plant_id}"
    log_event("plant_deleted", f"Plant '{name}' removed from garden")


# Handle update plant status
def update_plant_status(plant_id: int, status: str) -> None:
    conn = _connect()
    conn.execute("UPDATE plants SET status = ? WHERE id = ?", (status, plant_id))
    conn.commit()
    conn.close()
    _invalidate_caches()
    log_event("status_changed", f"Plant #{plant_id} status -> '{status}'")


# Handle update plant
def update_plant(plant_id: int, **fields) -> None:
    allowed = {"name", "name_nepali", "water_freq_hours", "notes", "status",
               "season", "soil_type", "water_need", "scientific_name", "planted_on", "image_path"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates: return
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [plant_id]
    conn = _connect()
    conn.execute(f"UPDATE plants SET {set_clause} WHERE id = ?", values)
    if "water_freq_hours" in updates:
        plant = get_plant(plant_id)
        if plant and plant.get("last_watered_at"):
            last = datetime.fromisoformat(plant["last_watered_at"])
            next_w = (last + timedelta(hours=updates["water_freq_hours"])).isoformat()
            conn.execute("UPDATE plants SET next_water_at = ? WHERE id = ?", (next_w, plant_id))
    conn.commit()
    conn.close()
    _invalidate_caches()
    log_event("plant_updated", f"Plant #{plant_id} updated: {list(updates.keys())}")



# Mark watered
def mark_watered(plant_id: int) -> dict:
    now = datetime.now()
    plant = get_plant(plant_id)
    if not plant: return {}
    on_time = 1
    if plant.get("next_water_at"):
        try:
            due = datetime.fromisoformat(plant["next_water_at"])
            on_time = 1 if now <= due + timedelta(hours=2) else 0
        except ValueError: pass
    streak = plant.get("streak", 0)
    streak = streak + 1 if on_time else 1
    longest = max(plant.get("longest_streak", 0), streak)
    total = plant.get("total_waterings", 0) + 1
    next_water = (now + timedelta(hours=plant["water_freq_hours"])).isoformat()
    conn = _connect()
    conn.execute("INSERT INTO watering_log (plant_id, watered_at, on_time) VALUES (?, ?, ?)", (plant_id, now.isoformat(), on_time))
    conn.execute(
        "UPDATE plants SET last_watered_at = ?, next_water_at = ?, streak = ?, "
        "longest_streak = ?, total_waterings = ?, status = 'healthy' WHERE id = ?",
        (now.isoformat(), next_water, streak, longest, total, plant_id),
    )
    conn.commit()
    conn.close()
    _invalidate_caches()
    log_event("watered", f"Plant '{plant['name']}' watered (streak={streak}, on_time={bool(on_time)})")
    return {"streak": streak, "longest_streak": longest, "on_time": bool(on_time), "total": total}


# Return last watered
def get_last_watered(plant_id: int) -> Optional[str]:
    conn = _connect()
    row = conn.execute("SELECT watered_at FROM watering_log WHERE plant_id = ? ORDER BY id DESC LIMIT 1", (plant_id,)).fetchone()
    conn.close()
    return row["watered_at"] if row else None


# Return watering history
def get_watering_history(plant_id: int, limit: int = 30) -> list[dict]:
    conn = _connect()
    rows = conn.execute("SELECT * FROM watering_log WHERE plant_id = ? ORDER BY id DESC LIMIT ?", (plant_id, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Return overdue plants
def get_overdue_plants() -> list[dict]:
    now = _now_iso()
    gid = get_current_garden_id()
    conn = _connect()
    try:
        if gid:
            rows = conn.execute(
                "SELECT * FROM plants WHERE garden_id = ? AND next_water_at IS NOT NULL AND next_water_at < ? ORDER BY next_water_at ASC",
                (gid, now),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM plants WHERE next_water_at IS NOT NULL AND next_water_at < ? ORDER BY next_water_at ASC",
                (now,),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# Return upcoming waterings
def get_upcoming_waterings(hours_ahead: float = 4) -> list[dict]:
    now = datetime.now()
    cutoff = (now + timedelta(hours=hours_ahead)).isoformat()
    gid = get_current_garden_id()
    conn = _connect()
    try:
        if gid:
            rows = conn.execute(
                "SELECT * FROM plants WHERE garden_id = ? AND next_water_at IS NOT NULL AND next_water_at > ? AND next_water_at <= ? ORDER BY next_water_at ASC",
                (gid, now.isoformat(), cutoff),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM plants WHERE next_water_at IS NOT NULL AND next_water_at > ? AND next_water_at <= ? ORDER BY next_water_at ASC",
                (now.isoformat(), cutoff),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# Handle auto update statuses
def auto_update_statuses() -> int:
    overdue = get_overdue_plants()
    changed = 0
    conn = _connect()
    for p in overdue:
        if p["status"] != "needs_water":
            conn.execute("UPDATE plants SET status = 'needs_water' WHERE id = ?", (p["id"],))
            changed += 1
    conn.commit()
    conn.close()
    if changed:
        _invalidate_caches()
        log_event("auto_status", f"{changed} plant(s) auto-set to needs_water")
    return changed



# Handle week start date
def _week_start_date(d: datetime) -> str:
    start = d - timedelta(days=d.weekday())
    return start.date().isoformat()


# Add checkin
def add_checkin(plant_id: int, height_cm: float, new_leaves: int,
                flowering: bool, note: str = "", image_path: str = "") -> int:
    week_date = datetime.now().date().isoformat()
    conn = _connect()
    conn.execute("DROP INDEX IF EXISTS idx_weekly_checkins_plant_week")
    cur = conn.execute(
        "INSERT INTO weekly_checkins (plant_id, week_date, height_cm, new_leaves, flowering, note, image_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (plant_id, week_date, height_cm, new_leaves, int(flowering), note, image_path),
    )
    cid = cur.lastrowid
    conn.commit()
    conn.close()
    _invalidate_caches()
    log_event("checkin", f"Check-in for plant #{plant_id}")
    return cid


# Return checkins
def get_checkins(plant_id: int) -> list[dict]:
    conn = _connect()
    rows = conn.execute("SELECT * FROM weekly_checkins WHERE plant_id = ? ORDER BY week_date DESC, id DESC", (plant_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]



# Add message
def add_message(
    content: str,
    sender: str = "System",
    msg_type: str = "info",
    user_id: Optional[int] = None,
    family_id: Optional[int] = None,
    garden_id: Optional[str] = None,
) -> None:
    now = _now_iso()
    if user_id is None and garden_id is None and family_id is None:
        garden_id = get_current_garden_id()

    conn = _connect()
    conn.execute(
        "INSERT INTO messages (sender, content, msg_type, created_at, user_id, family_id, garden_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (sender, content, msg_type, now, user_id, family_id, str(garden_id) if garden_id else None),
    )
    conn.commit()
    conn.close()
    _invalidate_caches()


# Return messages
def get_messages(limit: int = 50, include_family: bool = True) -> list[dict]:
    user = get_current_user()
    if not user:
        return []
    gid = str(user.get("garden_id") or "").strip() if include_family else ""
    uid = user.get("id")

    params: list = []
    where: list[str] = []
    if uid is not None:
        where.append("user_id = ?")
        params.append(int(uid))
    if gid:
        where.append("garden_id = ?")
        params.append(gid)

    if not where:
        return []

    conn = _connect()
    try:
        sql = f"SELECT * FROM messages WHERE ({' OR '.join(where)}) ORDER BY id DESC LIMIT ?"
        params.append(int(limit))
        rows = conn.execute(sql, tuple(params)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# Return garden members
def get_garden_members(garden_id: Optional[str] = None) -> list[dict]:
    gid = str(garden_id or get_current_garden_id() or "")
    if not gid:
        return []
    return _cached_get_garden_members(gid)


# Return user gardens
def get_user_gardens(user_id: Optional[int] = None) -> list[dict]:
    uid = user_id if user_id is not None else get_current_user_id()
    if uid is None:
        return []
    return _cached_get_user_gardens(int(uid))


# Switch user garden
def switch_user_garden(garden_id: str) -> bool:
    """Switch the current user's active garden by updating users.garden_id and session."""
    gid = (garden_id or "").strip()
    if not gid:
        return False
    if not garden_exists(gid):
        return False
    user = get_current_user()
    if not user or not user.get("id"):
        return False
    conn = _connect()
    try:
        conn.execute("UPDATE users SET garden_id = ? WHERE id = ?", (gid, int(user["id"])))
        conn.commit()
    finally:
        conn.close()
    user["garden_id"] = gid
    set_current_user(user)
    return True


# Handle update user theme pref
def update_user_theme_pref(user_id: int, theme_pref: str) -> bool:
    """Persist a user's light/dark theme preference."""
    uid = int(user_id)
    pref = (theme_pref or "light").strip().lower()
    if pref not in ("light", "dark"):
        pref = "light"

    conn = _connect()
    try:
        conn.execute("UPDATE users SET theme_pref = ? WHERE id = ?", (pref, uid))
        conn.commit()
    finally:
        conn.close()

    if _current_user and int(_current_user.get("id") or -1) == uid:
        _current_user["theme_pref"] = pref
    _invalidate_caches()
    return True


# Invite user to garden
def invite_user_to_garden(username: str, garden_id: Optional[str] = None) -> tuple[bool, str]:
    """Create a pending invite for a username into a garden."""
    inviter = get_current_user() or {}
    inviter_name = str(inviter.get("username") or "")
    inviter_id = inviter.get("id")
    gid = str(garden_id or inviter.get("garden_id") or "").strip()
    if not gid:
        return False, "No active garden to invite into"
    if not (gid.isdigit() and len(gid) == 6):
        return False, "Invalid garden ID"
    if not garden_exists(gid):
        return False, "Garden not found"

    target_norm = _normalize_username(username)
    if not target_norm:
        return False, "Enter a username"

    if inviter_name and _normalize_username(inviter_name) == target_norm:
        return False, "You are already in this garden"

    conn = _connect()
    try:
        existing_user = conn.execute(
            "SELECT id, username, garden_id FROM users WHERE lower(trim(username)) = ? LIMIT 1",
            (target_norm,),
        ).fetchone()
        if existing_user and str(existing_user["garden_id"] or "") == gid:
            return False, f"{existing_user['username']} is already in this garden"

        dup = conn.execute(
            "SELECT id FROM garden_invites WHERE garden_id = ? AND invited_username = ? AND status = 'pending' LIMIT 1",
            (gid, target_norm),
        ).fetchone()
        if dup:
            return False, "Invite already pending for this username"

        conn.execute(
            "INSERT INTO garden_invites (garden_id, invited_username, invited_by_user_id, status, created_at) "
            "VALUES (?, ?, ?, 'pending', ?)",
            (gid, target_norm, int(inviter_id) if inviter_id is not None else None, _now_iso()),
        )

        if existing_user:
            conn.execute(
                "INSERT INTO messages (sender, content, msg_type, created_at, user_id, garden_id) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    "Garden Invite",
                    f"You were invited to garden {gid} by {inviter_name or 'a member'}. Open Create Account/Invite Inbox to accept.",
                    "info",
                    _now_iso(),
                    int(existing_user["id"]),
                    gid,
                ),
            )

        conn.commit()
    finally:
        conn.close()

    _invalidate_caches()
    return True, f"Invite sent to @{target_norm}"


# Handle cached get pending invites
@functools.lru_cache(maxsize=128)
def _cached_get_pending_invites(invited_username: str) -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT i.id, i.garden_id, i.invited_username, i.created_at,
                   g.name AS garden_name,
                   u.username AS invited_by_username
              FROM garden_invites i
              LEFT JOIN gardens g ON g.garden_id = i.garden_id
              LEFT JOIN users u ON u.id = i.invited_by_user_id
             WHERE i.invited_username = ? AND i.status = 'pending'
             ORDER BY i.id DESC
            """,
            (invited_username,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# Return pending invites
def get_pending_invites(username: str) -> list[dict]:
    normalized = _normalize_username(username)
    if not normalized:
        return []
    return _cached_get_pending_invites(normalized)



# Add catalogue item
def add_catalogue_item(name: str, name_nepali: str = "", scientific_name: str = "", season: str = "", soil_type: str = "", water_need: str = "medium", water_freq_hours: float = 24, description: str = "", difficulty: str = "easy") -> Optional[int]:
    conn = _connect()
    try:
        cur = conn.execute("INSERT INTO catalogue (name, name_nepali, scientific_name, season, soil_type, water_need, water_freq_hours, description, difficulty) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (name, name_nepali, scientific_name, season, soil_type, water_need, water_freq_hours, description, difficulty))
        conn.commit()
        cid = cur.lastrowid
        _invalidate_caches()
        return cid
    except sqlite3.IntegrityError: return None
    finally: conn.close()


# Search catalogue
def search_catalogue(query: str = "") -> list[dict]:
    return _cached_search_catalogue(query or "")


# Return catalogue item
def get_catalogue_item(item_id: int) -> Optional[dict]:
    return _cached_get_catalogue_item(item_id)



# Log event
def log_event(event_type: str, details: str = "") -> None:
    conn = _connect()
    conn.execute("INSERT INTO event_log (timestamp, event_type, details) VALUES (?, ?, ?)", (datetime.now().isoformat(), event_type, details))
    conn.commit()
    conn.close()
    try: get_events.cache_clear()
    except: pass


# Return events
@functools.lru_cache(maxsize=8)
def get_events(limit: int = 100) -> list[dict]:
    conn = _connect()
    rows = conn.execute("SELECT * FROM event_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Clear events
def clear_events() -> None:
    conn = _connect()
    conn.execute("DELETE FROM event_log")
    conn.commit()
    conn.close()
    try:
        get_events.cache_clear()
    except Exception:
        pass


# Return table counts
def get_table_counts() -> dict[str, int]:
    conn = _connect()
    tables = ["plants", "watering_log", "weekly_checkins", "messages", "catalogue", "event_log"]
    counts = {t: conn.execute(f"SELECT COUNT(*) as c FROM {t}").fetchone()["c"] for t in tables}
    conn.close()
    return counts


# Return raw table
def get_raw_table(table: str, limit: int = 50) -> list[dict]:
    allowed = {"plants", "watering_log", "weekly_checkins", "messages", "catalogue", "event_log"}
    if table not in allowed: return []
    conn = _connect()
    rows = conn.execute(f"SELECT * FROM {table} ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Handle nuke garden
def nuke_garden() -> None:
    gid = get_current_garden_id()
    conn = _connect()
    try:
        if gid:
            plants = conn.execute("SELECT id FROM plants WHERE garden_id = ?", (gid,)).fetchall()
            for p in plants:
                try:
                    conn.execute("DELETE FROM watering_log WHERE plant_id = ?", (p["id"],))
                    conn.execute("DELETE FROM weekly_checkins WHERE plant_id = ?", (p["id"],))
                except Exception:
                    pass
            conn.execute("DELETE FROM plants WHERE garden_id = ?", (gid,))
        conn.commit()
    finally:
        conn.close()
    _invalidate_caches()
    log_event("nuke", f"Garden data wiped for garden_id={gid}")


# Handle nuke all data
def nuke_all_data(
    family_only: bool = True,
    delete_messages: bool = False,
    delete_events: bool = False,
) -> None:
    """Legacy signature retained. family_only now means "current garden only"."""
    gid = get_current_garden_id()
    conn = _connect()
    try:
        if family_only and gid:
            plant_ids = [
                int(r["id"]) for r in conn.execute(
                    "SELECT id FROM plants WHERE garden_id = ?", (gid,)
                ).fetchall()
            ]
            if plant_ids:
                q = ",".join("?" for _ in plant_ids)
                conn.execute(f"DELETE FROM watering_log WHERE plant_id IN ({q})", tuple(plant_ids))
                conn.execute(f"DELETE FROM weekly_checkins WHERE plant_id IN ({q})", tuple(plant_ids))
            conn.execute("DELETE FROM plants WHERE garden_id = ?", (gid,))
            if delete_messages:
                conn.execute("DELETE FROM messages WHERE garden_id = ?", (gid,))
        else:
            conn.execute("DELETE FROM watering_log")
            conn.execute("DELETE FROM weekly_checkins")
            conn.execute("DELETE FROM plants")
            if delete_messages:
                conn.execute("DELETE FROM messages")
        if delete_events:
            conn.execute("DELETE FROM event_log")
        conn.commit()
    finally:
        conn.close()
    _invalidate_caches()


# Clear messages
def clear_messages(current_scope_only: bool = True) -> int:
    """Clear relay messages for current garden/user scope or globally."""
    gid = get_current_garden_id()
    uid = get_current_user_id()

    conn = _connect()
    try:
        if current_scope_only and (gid or uid):
            where: list[str] = []
            params: list = []
            if gid:
                where.append("garden_id = ?")
                params.append(gid)
            if uid is not None:
                where.append("user_id = ?")
                params.append(int(uid))
            sql = f"DELETE FROM messages WHERE {' OR '.join(where)}"
            cur = conn.execute(sql, tuple(params))
        else:
            cur = conn.execute("DELETE FROM messages")
        conn.commit()
        deleted = int(cur.rowcount or 0)
    finally:
        conn.close()
    _invalidate_caches()
    return deleted


# Handle time warp plant
def time_warp_plant(plant_id: int, hours_back: float) -> bool:
    """Move a plant's next watering time backward by N hours for testing."""
    plant = get_plant(plant_id)
    if not plant:
        return False

    gid = get_current_garden_id()
    if gid and str(plant.get("garden_id") or "") != str(gid):
        return False

    try:
        hours = float(hours_back)
    except Exception:
        return False
    if hours <= 0:
        return False

    base = plant.get("next_water_at")
    try:
        base_dt = datetime.fromisoformat(str(base)) if base else datetime.now()
    except Exception:
        base_dt = datetime.now()

    warped = (base_dt - timedelta(hours=hours)).isoformat()
    status = "needs_water" if datetime.fromisoformat(warped) <= datetime.now() else plant.get("status", "healthy")

    conn = _connect()
    try:
        conn.execute(
            "UPDATE plants SET next_water_at = ?, status = ? WHERE id = ?",
            (warped, status, plant_id),
        )
        conn.commit()
    finally:
        conn.close()

    _invalidate_caches()
    log_event("time_warp", f"Plant #{plant_id} warped by {hours}h")
    return True


# Seed demo garden
def seed_demo_garden() -> int:
    """Seed random demo plants with randomized watering status/timing."""
    gid = get_current_garden_id()
    if not gid:
        return 0

    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT name, name_nepali, water_freq_hours, season, soil_type, water_need "
            "FROM catalogue WHERE trim(coalesce(name, '')) <> ''"
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return 0

    pick_count = min(len(rows), random.randint(4, 8))
    picked = random.sample(list(rows), pick_count)

    created = 0
    for r in picked:
        name = str(r["name"] or "").strip()
        if not name:
            continue

        freq_h = float(r["water_freq_hours"] or 24)
        pid = add_plant(
            name=name,
            name_nepali=str(r["name_nepali"] or "").strip(),
            water_freq_hours=freq_h,
            notes="Seeded by Dev Panel (randomized)",
            season=str(r["season"] or "").strip(),
            soil_type=str(r["soil_type"] or "").strip(),
            water_need=str(r["water_need"] or "medium").strip() or "medium",
        )

        if pid is not None:
            now = datetime.now()
            mode = random.choice(["overdue", "soon", "ok", "sick"])
            if mode == "overdue":
                next_dt = now - timedelta(hours=random.uniform(1, 24))
                status = "needs_water"
            elif mode == "soon":
                next_dt = now + timedelta(minutes=random.randint(5, 55))
                status = "healthy"
            elif mode == "sick":
                next_dt = now + timedelta(hours=random.uniform(1, 10))
                status = "sick"
            else:
                next_dt = now + timedelta(hours=random.uniform(2, 30))
                status = "healthy"

            last_dt = next_dt - timedelta(hours=max(freq_h, 1.0))
            c2 = _connect()
            try:
                c2.execute(
                    "UPDATE plants SET status = ?, next_water_at = ?, last_watered_at = ? WHERE id = ?",
                    (status, next_dt.isoformat(), last_dt.isoformat(), pid),
                )
                c2.commit()
            finally:
                c2.close()

        created += 1

    if created:
        _invalidate_caches()
        log_event("seed_demo", f"{created} random demo plants added")
    return created


