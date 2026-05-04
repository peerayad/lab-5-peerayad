-- Run in Supabase SQL Editor (Step 1 — borrow_requests lifecycle table)
-- Status flow: pending_approval → approved → pending_return → returned

CREATE TABLE borrow_requests (
  id bigserial PRIMARY KEY,
  equipment_id bigint REFERENCES equipment(id),
  asset_tag text,
  equipment_name text,
  student_name text NOT NULL,
  requested_at timestamptz DEFAULT now(),
  approver_name text,
  approved_at timestamptz,
  returned_at timestamptz,
  confirmer_name text,
  confirmed_at timestamptz,
  status text DEFAULT 'pending_approval'
);
