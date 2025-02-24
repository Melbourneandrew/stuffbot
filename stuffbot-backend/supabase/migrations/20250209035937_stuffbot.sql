create table if not exists stuff (
    id uuid primary key default gen_random_uuid(),
    created_at timestamp with time zone default now(),
    class text default 'unknown',
    approximate_price decimal(10,2),
    location_description text,
    full_image_id text,
    partial_image_id text,
    constraint valid_price check (approximate_price >= 0)
);

-- Enable RLS on the stuff table
alter table stuff enable row level security;

-- Create a policy that allows anyone to read the stuff table
create policy "Anyone can read stuff"
on stuff for select
to anon
using (true);

-- Create a policy that allows anyone to insert into the stuff table
create policy "Anyone can insert stuff"
on stuff for insert
to anon
with check (true);

-- Create a policy that allows anyone to update the stuff table
create policy "Anyone can update stuff"
on stuff for update
to anon
using (true)
with check (true);

-- Create a policy that allows anyone to delete from the stuff table
create policy "Anyone can delete stuff"
on stuff for delete
to anon
using (true);

-- Make the storage bucket public
insert into storage.buckets (id, name, public)
values ('stuff_images_bucket', 'stuff_images_bucket', true)
on conflict (id) do update set public = true;

-- Add storage policies for the bucket
create policy "Anyone can read stuff images"
on storage.objects for select
to anon
using (bucket_id = 'stuff_images_bucket');

create policy "Anyone can upload stuff images"
on storage.objects for insert
to anon
with check (bucket_id = 'stuff_images_bucket');

-- Drop existing trigger if it exists
drop trigger if exists classify_stuff_images_webhook on stuff;

-- Create a webhook trigger for image classification (only on INSERT)
create trigger classify_stuff_images_webhook
after insert on stuff
for each row
execute function supabase_functions.http_request(
  'http://host.docker.internal:54321/functions/v1/classify_image',
  'POST',
  '{"Content-Type":"application/json"}',
  '{}',
  '10000'
);