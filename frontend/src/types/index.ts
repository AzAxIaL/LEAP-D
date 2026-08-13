// TypeScript type definitions

export interface Course {
  id: number
  name: string
  description: string | null
  retention_days: number
  is_archived: boolean
  created_at: string
  updated_at: string | null
}

export interface Student {
  id: number
  stable_id: string
  first_name: string
  course_id: number
  is_active: boolean
  created_at: string
  updated_at: string | null
}

export interface Session {
  id: number
  course_id: number
  name: string
  description: string | null
  recorded_at: string | null
  task_type: string | null
  audio_source_type: 'multi_track' | 'mixed_file'
  created_at: string
  updated_at: string | null
}

export interface AudioFile {
  id: number
  session_id: number
  original_filename: string
  stored_path: string
  content_hash: string
  file_size_bytes: number
  duration_seconds: number
  sample_rate: number
  channels: number
  codec: string | null
  import_source: string
  imported_at: string
  is_processed: boolean
  processed_path: string | null
}

export interface Job {
  id: number
  session_id: number
  job_type: string
  status: 'pending' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
  current_stage: string | null
  progress_percent: number
  error_message: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
}

export interface Utterance {
  id: number
  transcript_id: number
  speaker_label: string
  start_time: number
  end_time: number
  text: string
  confidence: number | null
  is_reviewed: boolean
  words: Word[]
}

export interface Word {
  id: number
  utterance_id: number
  text: string
  start_time: number
  end_time: number
  confidence: number | null
}

export interface DisfluencyCandidate {
  id: number
  utterance_id: number
  disfluency_type: string
  start_time: number
  end_time: number
  evidence_text: string
  detector: string
  confidence: number
  review_status: 'pending' | 'accepted' | 'rejected' | 'needs_context'
}
