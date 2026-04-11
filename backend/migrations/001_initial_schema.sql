-- AgentVerse Multi-Agent Platform Database Schema
-- Migration: 001_initial_schema

-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- Tenants (multi-tenancy foundation)
create table tenants (
    id uuid primary key default uuid_generate_v4(),
    name varchar(255) not null,
    slug varchar(255) unique not null,
    plan varchar(50) default 'free',
    config jsonb default '{}',
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

-- Projects (business units)
create table projects (
    id uuid primary key default uuid_generate_v4(),
    tenant_id uuid not null references tenants(id) on delete cascade,
    name varchar(255) not null,
    description text,
    type varchar(50) default 'general',
    status varchar(50) default 'active',
    config jsonb default '{}',
    created_by uuid,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

-- Rooms (shared workspaces)
create table rooms (
    id uuid primary key default uuid_generate_v4(),
    project_id uuid not null references projects(id) on delete cascade,
    name varchar(255) not null,
    description text,
    room_type varchar(50) default 'general',
    shared_context jsonb default '{}',
    artifact_urls text[] default '{}',
    guidelines jsonb default '{}',
    status varchar(50) default 'active',
    is_private boolean default false,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

-- Agents (reusable definitions)
create table agents (
    id uuid primary key default uuid_generate_v4(),
    tenant_id uuid not null references tenants(id) on delete cascade,
    name varchar(255) not null,
    role varchar(100) not null,
    avatar_url text,
    color varchar(7) default '#00f3ff',
    model varchar(100) default 'claude-3-sonnet',
    system_prompt text not null,
    temperature float default 0.7,
    max_tokens int default 4096,
    tools text[] default '{}',
    allowed_rooms text[] default '{}',
    is_active boolean default true,
    total_tasks_completed int default 0,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

-- Room membership (presence)
create table room_agents (
    id uuid primary key default uuid_generate_v4(),
    room_id uuid not null references rooms(id) on delete cascade,
    agent_id uuid not null references agents(id) on delete cascade,
    status varchar(50) default 'idle',
    current_task_id uuid,
    position_x float default 0,
    position_y float default 0,
    position_z float default 0,
    entered_at timestamptz default now(),
    last_heartbeat timestamptz default now(),
    left_at timestamptz,
    unique(room_id, agent_id)
);

-- Tasks
create table tasks (
    id uuid primary key default uuid_generate_v4(),
    room_id uuid not null references rooms(id) on delete cascade,
    owner_agent_id uuid not null references agents(id),
    contributor_agent_ids uuid[] default '{}',
    type varchar(100) not null,
    title varchar(500) not null,
    description text,
    priority int default 3,
    status varchar(50) default 'pending',
    input_payload jsonb default '{}',
    output_payload jsonb default '{}',
    parent_task_id uuid references tasks(id),
    depends_on uuid[] default '{}',
    created_at timestamptz default now(),
    started_at timestamptz,
    completed_at timestamptz
);

-- Messages
create table messages (
    id uuid primary key default uuid_generate_v4(),
    room_id uuid not null references rooms(id) on delete cascade,
    from_agent_id uuid not null references agents(id),
    to_agent_id uuid references agents(id),
    message_type varchar(50) default 'chat',
    content text not null,
    metadata jsonb default '{}',
    reply_to uuid references messages(id),
    created_at timestamptz default now()
);

-- Activities
create table activities (
    id uuid primary key default uuid_generate_v4(),
    room_id uuid not null references rooms(id) on delete cascade,
    agent_id uuid references agents(id),
    task_id uuid references tasks(id),
    activity_type varchar(100) not null,
    description text not null,
    metadata jsonb default '{}',
    created_at timestamptz default now()
);

-- Indexes
create index idx_projects_tenant on projects(tenant_id);
create index idx_rooms_project on rooms(project_id);
create index idx_room_agents_room on room_agents(room_id);
create index idx_room_agents_agent on room_agents(agent_id);
create index idx_room_agents_status on room_agents(status) where status != 'offline';
create index idx_tasks_room on tasks(room_id);
create index idx_tasks_owner on tasks(owner_agent_id);
create index idx_tasks_status on tasks(status);
create index idx_messages_room on messages(room_id);
create index idx_messages_created on messages(created_at desc);
create index idx_activities_room on activities(room_id, created_at desc);

-- Seed data for development
insert into tenants (name, slug, plan) values ('Default Tenant', 'default', 'pro');

insert into projects (tenant_id, name, description, type) 
select id, 'Marketing Campaign Q4', 'Holiday marketing initiative', 'marketing'
from tenants where slug = 'default';

insert into rooms (project_id, name, description, room_type, shared_context)
select 
    p.id,
    'Strategy Room',
    'High-level planning and research',
    'strategy',
    '{"brief": "Launch holiday campaign targeting 25-34 demographic", "budget": 50000, "timeline": "6 weeks"}'::jsonb
from projects p
join tenants t on p.tenant_id = t.id
where t.slug = 'default';

insert into agents (tenant_id, name, role, system_prompt, color, tools)
select 
    id,
    'Researcher Alpha',
    'researcher',
    'You are a market research specialist. Analyze trends, identify opportunities, and provide data-backed insights.',
    '#00f3ff',
    '{"web_search", "trend_analysis"}'
from tenants where slug = 'default';
