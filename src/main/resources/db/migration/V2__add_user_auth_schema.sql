
CREATE TABLE app_role (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255)
);

CREATE TABLE app_user (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE,
    password VARCHAR(255)
);

CREATE TABLE app_user_roles (
    app_user_id BIGINT REFERENCES app_user(id),
    roles_id BIGINT REFERENCES app_role(id)
);

INSERT INTO app_role (name) VALUES ('ROLE_USER'), ('ROLE_ADMIN');
INSERT INTO app_user (username, password) VALUES ('admin', '$2a$10$NmYLepwmeTRL8dB.zFJq2el6vvOsMfHLnJ0urGp052ib71Il6V66m'); -- password: admin123
INSERT INTO app_user_roles (app_user_id, roles_id) VALUES (1, 1), (1, 2);
