# Changelog

All notable changes to LinguaSight will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project scaffold with backend (FastAPI) and frontend (React + TypeScript + Vite)
- Database models for courses, students, sessions, audio files, transcripts, jobs
- Alembic migrations configuration
- ASR provider interface supporting Whisper, faster-whisper, WhisperX, crisperwhisper
- Disfluency detection service with hybrid pipeline
- Fluency metrics computation with eligibility flags
- CEFR evidence profile framework
- PowerShell and bash setup/run scripts
- Comprehensive README documentation
- Acceptance checklist mapped to specification

### Changed
- N/A

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- N/A

### Security
- Privacy-first design with first names only
- Consent tracking before voiceprint enrollment
- Local-only processing by default (no cloud audio upload)
- API keys stored in environment variables only

---

## Version Legend

- **Added** for new features.
- **Changed** for changes in existing functionality.
- **Deprecated** for soon-to-be removed features.
- **Removed** for now removed features.
- **Fixed** for any bug fixes.
- **Security** in case of vulnerabilities.
