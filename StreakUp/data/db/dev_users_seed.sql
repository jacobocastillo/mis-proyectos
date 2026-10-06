-- =====================================================
-- LOCAL DEMO USERS
-- =====================================================
-- Development-only seed. Do not use in hosted deployments.

INSERT OR IGNORE INTO users (username, email, password_hash, role, total_xp)
VALUES
(
    'Daniel',
    'daniel@correo.com',
    'scrypt:32768:8:1$WikUmFaQkTvl4lH7$cd5b95153c1b0a72ec8d9e39dd4bfb7654e6b12552d34c7637157d2d6f7cc675db5644ce36416e5711cde5801440110a2d4a83236628fa53f4a3154c80910bb8',
    'user',
    0
),
(
    'Gustavo',
    'gustavo@correo.com',
    'scrypt:32768:8:1$TEHtUakfY18WCOcp$807220279ffea8610447d0bf83a1f8bb112f49ec49bd989b203e5fb21c51213a76d7938d48c1f826bb985e32a81b823a2b5546eb2d1ed5f1a3a34463c3717d80',
    'user',
    0
),
(
    'Adrian',
    'adrian@correo.com',
    'scrypt:32768:8:1$cWJQ9BTuaFCv82Sy$b90fbb8797c36594e1ff0bf71d789e4757757db8910b1aead4cb02acd01311d98f7e4771d1bebb1a3e2851bbfe6a67741c24b6b52587da6135dbc5c6b039c875',
    'user',
    0
),
(
    'Prueba',
    'prueba@correo.com',
    'scrypt:32768:8:1$ifWQRcoPaFDoct0u$4a8695472ce8835fd478499e2633f469cdcaaf8609fa68afd2ae294379928845e0c66247c17b32b4d85844a61c63757fc2abac3bcfee0a817ffbc87867f9058d',
    'user',
    0
);
