CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE nodes (
    id  SERIAL PRIMARY KEY,
    ip INET,
    system TEXT,
    name TEXT UNIQUE,
    release TEXT,
    version TEXT,
    type TEXT
);

CREATE TABLE cpu (
    id SERIAL,
    node_id INTEGER REFERENCES nodes(id) ON DELETE CASCADE,
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    load DOUBLE PRECISION, 
    frequency DOUBLE PRECISION,
    avg_load DOUBLE PRECISION,
    last_start TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (id, time)
);

CREATE TABLE ram_memory (
    id SERIAL,
    node_id INTEGER REFERENCES nodes(id) ON DELETE CASCADE,
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    total BIGINT,
    available BIGINT,
    percent DOUBLE PRECISION,
    used BIGINT,
    free BIGINT,
    active BIGINT,
    inactive BIGINT,
    buffers BIGINT,
    cached BIGINT,
    shared BIGINT,
    slab BIGINT,
    PRIMARY KEY (id, time)
);

CREATE TABLE swap_memory(
    id SERIAL,
    node_id INTEGER REFERENCES nodes(id) ON DELETE CASCADE,
    time TIMESTAMP WITH TIME ZONE NOT NULL,  
    total BIGINT, 
    used BIGINT,
    free BIGINT,
    percent DOUBLE PRECISION,
    sin BIGINT,
    sout BIGINT,
    PRIMARY KEY (id, time)
);

CREATE TABLE process (
    id SERIAL,
    node_id INTEGER REFERENCES nodes(id) ON DELETE CASCADE,
    time TIMESTAMP WITH TIME ZONE NOT NULL,   
    pid INTEGER,
    process_name TEXT,
    ram_used BIGINT,
    PRIMARY KEY (id, time)
);

CREATE TABLE hard_memory(
    id SERIAL,
    node_id INTEGER REFERENCES nodes(id) ON DELETE CASCADE,
    time TIMESTAMP WITH TIME ZONE NOT NULL,  
    name TEXT,
    total BIGINT,
    used BIGINT,
    free BIGINT,
    percent DOUBLE PRECISION,
    PRIMARY KEY (id, time)   
);

CREATE TABLE temperatures(
    id SERIAL,
    node_id INTEGER REFERENCES nodes(id) ON DELETE CASCADE,
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    acpitz DOUBLE PRECISION,
    nvme DOUBLE PRECISION,
    coretemp DOUBLE PRECISION,
    nic_adapter DOUBLE PRECISION,
    PRIMARY KEY (id, time)   
);

SELECT create_hypertable('cpu', 'time');
SELECT create_hypertable('ram_memory', 'time');
SELECT create_hypertable('swap_memory', 'time');
SELECT create_hypertable('process', 'time');
SELECT create_hypertable('hard_memory', 'time');
SELECT create_hypertable('temperatures', 'time');

CREATE OR REPLACE PROCEDURE parse_agent_data(payload JSONB)
LANGUAGE plpgsql
AS $$
DECLARE
    v_node_id INTEGER;
    v_time TIMESTAMP WITH TIME ZONE;
    disk_item JSONB;
    proc_item JSONB;
BEGIN
    v_time := (payload->>'time')::TIMESTAMP WITH TIME ZONE;

    INSERT INTO nodes (ip, system, name, release, version, type)
    VALUES (
        (payload->'node'->>'ip')::INET,
        payload->'node'->>'system',
        payload->'node'->>'name',
        payload->'node'->>'release',
        payload->'node'->>'version',
        payload->'node'->>'type'
    )
    ON CONFLICT (name) DO UPDATE
    SET ip = EXCLUDED.ip, version = EXCLUDED.version
    RETURNING id INTO v_node_id;

    INSERT INTO cpu (node_id, time, load, frequency, avg_load, last_start)
    VALUES (v_node_id, v_time,
        (payload->'cpu'->>'load')::DOUBLE PRECISION,
        (payload->'cpu'->>'frequency')::DOUBLE PRECISION,
        (payload->'cpu'->>'avg_load')::DOUBLE PRECISION,
        (payload->'cpu'->>'last_start')::TIMESTAMP WITH TIME ZONE);

    INSERT INTO ram_memory (node_id, time, total, available, percent, used, free, active, inactive, buffers, cached, shared, slab)
    VALUES (v_node_id, v_time,
        (payload->'ram'->>'total')::BIGINT,
        (payload->'ram'->>'available')::BIGINT,
        (payload->'ram'->>'percent')::DOUBLE PRECISION,
        (payload->'ram'->>'used')::BIGINT,
        (payload->'ram'->>'free')::BIGINT,
        (payload->'ram'->>'active')::BIGINT,
        (payload->'ram'->>'inactive')::BIGINT,
        (payload->'ram'->>'buffers')::BIGINT,
        (payload->'ram'->>'cached')::BIGINT,
        (payload->'ram'->>'shared')::BIGINT,
        (payload->'ram'->>'slab')::BIGINT);

    INSERT INTO swap_memory (node_id, time, total, used, free, percent, sin, sout)
    VALUES (v_node_id, v_time,
        (payload->'swap'->>'total')::BIGINT,
        (payload->'swap'->>'used')::BIGINT,
        (payload->'swap'->>'free')::BIGINT,
        (payload->'swap'->>'percent')::DOUBLE PRECISION,
        (payload->'swap'->>'sin')::BIGINT,
        (payload->'swap'->>'sout')::BIGINT);

    INSERT INTO temperatures (node_id, time, acpitz, nvme, coretemp, nic_adapter)
    VALUES (v_node_id, v_time, 
        (payload->'temperatures'->>'acpitz')::DOUBLE PRECISION,
        (payload->'temperatures'->>'nvme')::DOUBLE PRECISION,
        (payload->'temperatures'->>'coretemp')::DOUBLE PRECISION,
        (payload->'temperatures'->>'nic_adapter')::DOUBLE PRECISION);

    FOR disk_item IN SELECT * FROM jsonb_array_elements(payload->'disks') LOOP
        INSERT INTO hard_memory (node_id, time, name, total, used, free, percent)
        VALUES (v_node_id, v_time,
        disk_item->>'name',
        (disk_item->>'total')::BIGINT,
        (disk_item->>'used')::BIGINT,
        (disk_item->>'free')::BIGINT,
        (disk_item->>'percent')::DOUBLE PRECISION);
    END LOOP;

    FOR proc_item IN SELECT * FROM jsonb_array_elements(payload->'processes') LOOP
        INSERT INTO process (node_id, time, pid, process_name, ram_used)
        VALUES (v_node_id, v_time,
        (proc_item->>'pid')::INTEGER,
        proc_item->>'process_name',
        (proc_item->>'ram_used')::BIGINT);
    END LOOP;
END;
$$;   