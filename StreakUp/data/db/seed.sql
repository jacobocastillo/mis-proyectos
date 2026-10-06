-- =========================================
-- STREAKUP - SEED.SQL (LOCAL SQLITE)
-- Convenience seed for local SQLite resets only.
-- =========================================

PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

INSERT OR IGNORE INTO categorias (id, nombre, descripcion) VALUES
    (1, 'Salud y Bienestar', 'Hábitos físicos y mentales'),
    (2, 'Productividad', 'Enfoque y rendimiento'),
    (3, 'Aprendizaje', 'Lectura, idiomas y estudio');

INSERT OR IGNORE INTO habitos (
    id,
    categoria_id,
    nombre,
    descripcion,
    dificultad,
    xp_base,
    meta_type,
    xp_rate,
    max_xp_per_day,
    activo,
    tipo_validacion,
    frecuencia,
    cantidad_objetivo,
    unidad_objetivo,
    duracion_objetivo_minutos
) VALUES
    (1, 1, 'Beber 2L de agua', 'Mantener hidratación diaria', 'facil', 10, 'quantity_liters', 0, 20, 1, 'photo', 'daily', 2, 'litros', NULL),
    (2, 1, 'Ejercicio 30 min', 'Actividad física diaria', 'media', 0, 'minutes', 1, 60, 1, 'time', 'daily', NULL, NULL, 30),
    (3, 1, 'Comida saludable', 'Alimentación balanceada', 'media', 25, 'boolean', 0, 25, 1, 'photo', 'daily', NULL, NULL, NULL),
    (4, 1, 'Meditar 5-10 min', 'Relajación mental', 'facil', 10, 'minutes', 1, 25, 1, 'time', 'daily', NULL, NULL, 10),
    (5, 2, 'Día sin quejas', 'Mantener una mentalidad positiva', 'facil', 15, 'boolean', 0, 15, 1, 'text_ai', 'daily', NULL, NULL, NULL),
    (6, 2, 'Trabajo profundo 60 min', 'Sesión sin distracciones', 'dificil', 0, 'minutes', 1, 60, 1, 'time', 'daily', NULL, NULL, 60),
    (7, 2, 'Completar tarea clave', 'Tarea importante del día', 'media', 30, 'boolean', 0, 30, 1, 'text_ai', 'daily', NULL, NULL, NULL),
    (8, 2, 'Empezar antes de las 9am', 'Disciplina matutina', 'media', 20, 'boolean', 0, 20, 1, 'check', 'daily', NULL, NULL, NULL),
    (9, 3, 'Leer 20 min', 'Lectura diaria', 'facil', 0, 'minutes', 1, 30, 1, 'time', 'daily', NULL, NULL, 20),
    (10, 3, 'Practicar idioma', 'Aprendizaje lingüístico', 'media', 25, 'boolean', 0, 25, 1, 'text_ai', 'daily', NULL, NULL, NULL),
    (11, 3, 'Tender la cama', 'Ordenar el espacio al comenzar el día', 'facil', 10, 'boolean', 0, 10, 1, 'photo', 'daily', NULL, NULL, NULL),
    (12, 3, 'Dormir antes de medianoche', 'Rutina de descanso constante', 'media', 20, 'boolean', 0, 20, 1, 'check', 'daily', NULL, NULL, NULL);

COMMIT;
