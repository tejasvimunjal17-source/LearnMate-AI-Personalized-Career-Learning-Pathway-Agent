-- ============================================================================
-- LearnMate AI — One-time script: create the first super admin
-- admin_users is confirmed empty, so this is a plain insert (no conflict
-- to worry about, but ON CONFLICT is still included for safety if you
-- ever re-run it by accident).
--
-- Hashing: PostgreSQL's pgcrypto extension — crypt(password,
-- gen_salt('bf', 12)) — produces a standard bcrypt hash ($2a$12$...).
-- backend/admin_auth.py's verify_password() calls Python's
-- bcrypt.checkpw(plain_password, password_hash) against whatever string
-- is stored in admin_users.password_hash - it has no idea (and doesn't
-- care) whether that hash was produced by pgcrypto or Python's own
-- bcrypt.hashpw(). Both implement the same bcrypt algorithm, so a hash
-- from either one verifies correctly against the other. gen_salt('bf', 12)
-- matches bcrypt.gensalt()'s Python-side default cost factor (12).
-- ============================================================================

create extension if not exists pgcrypto;

insert into admin_users (email, password_hash, first_name, last_name, is_super_admin, is_active)
values (
    'satishgujjar618@gmail.com',
    crypt('Consistency@172007', gen_salt('bf', 12)),
    'Satish',              -- <- edit if you want a different first_name
    'Gujjar',               -- <- edit if you want a different last_name
    true,                    -- is_super_admin
    true                      -- is_active
)
on conflict (email) do nothing;

-- ============================================================================
-- Verification (safe to run - does not print the hash itself):
--
-- select email, first_name, last_name, is_super_admin, is_active,
--        left(password_hash, 4) as hash_prefix, created_at
-- from admin_users
-- where email = 'satishgujjar618@gmail.com';
--
-- Expect exactly 1 row, hash_prefix = '$2a$' (confirms a real bcrypt hash).
-- ============================================================================
