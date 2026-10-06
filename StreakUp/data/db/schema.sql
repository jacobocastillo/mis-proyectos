-- =========================================
-- STREAKUP - SCHEMA.SQL (LOCAL SQLITE)
-- Source of truth for hosted environments is Alembic + ORM.
-- This file remains a SQLite-only convenience for local resets.
-- =========================================

PRAGMA foreign_keys = ON;

-- =====================================================
-- USERS
-- =====================================================
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    fcm_token TEXT,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    total_xp INTEGER NOT NULL DEFAULT 0,
    level INTEGER NOT NULL DEFAULT 1,
    xp_in_level INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- =====================================================
-- CATEGORIAS
-- =====================================================
CREATE TABLE IF NOT EXISTS categorias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,
    descripcion TEXT
);

CREATE INDEX IF NOT EXISTS idx_categorias_nombre ON categorias(nombre);

-- =====================================================
-- HABITOS (CATALOGO)
-- =====================================================
CREATE TABLE IF NOT EXISTS habitos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    categoria_id INTEGER NOT NULL,
    nombre TEXT NOT NULL,
    descripcion TEXT,
    dificultad TEXT NOT NULL CHECK (dificultad IN ('facil','media','dificil')),
    xp_base INTEGER NOT NULL CHECK (xp_base >= 0),
    meta_type TEXT NOT NULL DEFAULT 'boolean',
    xp_rate INTEGER NOT NULL DEFAULT 0 CHECK (xp_rate >= 0),
    max_xp_per_day INTEGER NOT NULL DEFAULT 0 CHECK (max_xp_per_day >= 0),
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0,1)),
    tipo_validacion TEXT NOT NULL DEFAULT 'foto' CHECK (tipo_validacion IN ('foto','texto','tiempo','photo','text_ai','time','check')),
    frecuencia TEXT NOT NULL DEFAULT 'daily' CHECK (frecuencia IN ('daily','weekly')),
    cantidad_objetivo NUMERIC(8,2) CHECK (cantidad_objetivo IS NULL OR cantidad_objetivo >= 0),
    unidad_objetivo TEXT,
    duracion_objetivo_minutos INTEGER CHECK (duracion_objetivo_minutos IS NULL OR duracion_objetivo_minutos >= 0),
    FOREIGN KEY (categoria_id) REFERENCES categorias(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_habitos_categoria ON habitos(categoria_id);

-- =====================================================
-- HABITOS_USUARIO
-- =====================================================
CREATE TABLE IF NOT EXISTS habitos_usuario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    habito_id INTEGER NOT NULL,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE,
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0,1)),
    nombre_personalizado TEXT,
    descripcion_personalizada TEXT,
    tipo_validacion TEXT CHECK (tipo_validacion IS NULL OR tipo_validacion IN ('foto','texto','tiempo','photo','text_ai','time','check')),
    frecuencia TEXT CHECK (frecuencia IS NULL OR frecuencia IN ('daily','weekly','custom')),
    cantidad_objetivo NUMERIC(8,2) CHECK (cantidad_objetivo IS NULL OR cantidad_objetivo >= 0),
    unidad_objetivo TEXT,
    duracion_objetivo_minutos INTEGER CHECK (duracion_objetivo_minutos IS NULL OR duracion_objetivo_minutos >= 0),
    deadline_time TEXT CHECK (deadline_time IS NULL OR deadline_time GLOB '[0-2][0-9]:[0-5][0-9]'),
    min_text_length INTEGER CHECK (min_text_length IS NULL OR min_text_length >= 0),
    fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (habito_id) REFERENCES habitos(id) ON DELETE CASCADE,
    UNIQUE (usuario_id, habito_id, activo)
);

CREATE INDEX IF NOT EXISTS idx_habitos_usuario_usuario ON habitos_usuario(usuario_id);
CREATE INDEX IF NOT EXISTS idx_habitos_usuario_habito ON habitos_usuario(habito_id);

-- =====================================================
-- HABITOS_USUARIO_SCHEDULE
-- =====================================================
CREATE TABLE IF NOT EXISTS habitos_usuario_schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    habitousuario_id INTEGER NOT NULL,
    weekday INTEGER NOT NULL CHECK (weekday BETWEEN 0 AND 6),
    FOREIGN KEY (habitousuario_id) REFERENCES habitos_usuario(id) ON DELETE CASCADE,
    UNIQUE (habitousuario_id, weekday)
);

CREATE INDEX IF NOT EXISTS idx_habitos_usuario_schedule_habitousuario
ON habitos_usuario_schedule(habitousuario_id);

-- =====================================================
-- REGISTRO_HABITOS
-- =====================================================
CREATE TABLE IF NOT EXISTS registro_habitos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    habitousuario_id INTEGER NOT NULL,
    fecha DATE NOT NULL,
    completado INTEGER NOT NULL DEFAULT 1 CHECK (completado IN (0,1)),
    xp_ganado INTEGER NOT NULL DEFAULT 0 CHECK (xp_ganado >= 0),
    FOREIGN KEY (habitousuario_id) REFERENCES habitos_usuario(id) ON DELETE CASCADE,
    UNIQUE (habitousuario_id, fecha)
);

CREATE INDEX IF NOT EXISTS idx_registro_fecha ON registro_habitos(fecha);

-- =====================================================
-- VALIDACIONES
-- =====================================================
CREATE TABLE IF NOT EXISTS validaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    habitousuario_id INTEGER NOT NULL,
    tipo_validacion TEXT NOT NULL CHECK (tipo_validacion IN ('foto','texto','tiempo','manual')),
    evidencia TEXT,
    tiempo_segundos INTEGER,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected')),
    validado INTEGER NOT NULL DEFAULT 0 CHECK (validado IN (0,1)),
    fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (habitousuario_id) REFERENCES habitos_usuario(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_validaciones_habitousuario ON validaciones(habitousuario_id);

-- =====================================================
-- XP_LOGS
-- =====================================================
CREATE TABLE IF NOT EXISTS xp_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    cantidad INTEGER NOT NULL,
    fuente TEXT NOT NULL CHECK (fuente IN ('checkin','checkin_undo','validation')),
    fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    habit_id INTEGER REFERENCES habitos_usuario(id) ON DELETE SET NULL,
    event_date DATE,
    calculated_xp INTEGER,
    source_event TEXT NOT NULL DEFAULT 'habit' CHECK (source_event IN ('habit','achievement')),
    cap_hit INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (usuario_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_xp_logs_usuario ON xp_logs(usuario_id);
CREATE INDEX IF NOT EXISTS ix_xp_logs_habit_date ON xp_logs(usuario_id, habit_id, event_date);

-- =====================================================
-- POMODORO_SESSIONS
-- =====================================================
CREATE TABLE IF NOT EXISTS pomodoro_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    habit_id INTEGER,
    theme TEXT NOT NULL DEFAULT 'fire',
    study_minutes INTEGER NOT NULL DEFAULT 25 CHECK (study_minutes > 0),
    break_minutes INTEGER NOT NULL DEFAULT 5 CHECK (break_minutes >= 0),
    cycles INTEGER NOT NULL DEFAULT 4 CHECK (cycles > 0),
    completed INTEGER NOT NULL DEFAULT 0 CHECK (completed IN (0,1)),
    interruption_count INTEGER NOT NULL DEFAULT 0 CHECK (interruption_count >= 0),
    bonus_xp_awarded INTEGER,
    started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (habit_id) REFERENCES habitos_usuario(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_pomodoro_sessions_user_started
ON pomodoro_sessions(user_id, started_at);

-- =====================================================
-- ACHIEVEMENTS
-- =====================================================
CREATE TABLE IF NOT EXISTS achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    emoji TEXT NOT NULL DEFAULT '🏆',
    xp_bonus INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS ix_achievements_key ON achievements(key);

CREATE TABLE IF NOT EXISTS user_achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    achievement_id INTEGER NOT NULL,
    earned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (achievement_id) REFERENCES achievements(id) ON DELETE CASCADE,
    UNIQUE (user_id, achievement_id)
);

CREATE INDEX IF NOT EXISTS ix_user_achievements_user_id
ON user_achievements(user_id);

-- =====================================================
-- SHARED STREAK SOCIAL GROUPS
-- =====================================================
CREATE TABLE IF NOT EXISTS shared_streak_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_user_id INTEGER NOT NULL,
    habit_id INTEGER,
    winner_user_id INTEGER,
    name TEXT NOT NULL CHECK (length(name) >= 3),
    invite_code TEXT NOT NULL UNIQUE,
    max_participants INTEGER NOT NULL DEFAULT 3,
    start_date DATE NOT NULL DEFAULT CURRENT_DATE,
    duration_days INTEGER,
    end_date DATE,
    group_status TEXT NOT NULL DEFAULT 'active' CHECK (group_status IN ('active','finished')),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1)),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (habit_id) REFERENCES habitos(id) ON DELETE SET NULL,
    FOREIGN KEY (winner_user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_shared_streak_groups_owner_user_id
ON shared_streak_groups(owner_user_id);

CREATE INDEX IF NOT EXISTS ix_shared_streak_groups_invite_code
ON shared_streak_groups(invite_code);

CREATE TABLE IF NOT EXISTS shared_streak_memberships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    user_habit_id INTEGER,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','left','lost','winner')),
    share_progress INTEGER NOT NULL DEFAULT 1 CHECK (share_progress IN (0,1)),
    completed_days INTEGER NOT NULL DEFAULT 0,
    joined_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    left_at DATETIME,
    lost_at DATETIME,
    FOREIGN KEY (group_id) REFERENCES shared_streak_groups(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (user_habit_id) REFERENCES habitos_usuario(id) ON DELETE SET NULL,
    UNIQUE (group_id, user_id)
);

CREATE INDEX IF NOT EXISTS ix_shared_streak_memberships_group_id
ON shared_streak_memberships(group_id);

CREATE INDEX IF NOT EXISTS ix_shared_streak_memberships_user_id
ON shared_streak_memberships(user_id);

-- =====================================================
-- SYNC OPERATION RECEIPTS
-- =====================================================
CREATE TABLE IF NOT EXISTS sync_operations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    client_operation_id TEXT NOT NULL,
    operation_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('acked','failed','conflict')),
    response_json TEXT NOT NULL,
    error_code TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (user_id, client_operation_id)
);

CREATE INDEX IF NOT EXISTS ix_sync_operations_user_id
ON sync_operations(user_id);

-- =====================================================
-- NIVELES
-- =====================================================
CREATE TABLE IF NOT EXISTS niveles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    xp_minimo INTEGER NOT NULL,
    xp_maximo INTEGER NOT NULL,
    recompensa TEXT,
    descripcion TEXT,
    CHECK (xp_minimo < xp_maximo)
);

-- =====================================================
-- TOKEN BLOCKLIST (logout / revocation)
-- =====================================================
CREATE TABLE IF NOT EXISTS token_blocklist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    jti TEXT NOT NULL UNIQUE,
    token_type TEXT NOT NULL DEFAULT 'access',
    revoked_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_token_blocklist_jti ON token_blocklist(jti);
