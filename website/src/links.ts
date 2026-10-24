// Single source of truth for URLs and pinned release facts (from PROVENANCE.md / project facts).
export const BASE = import.meta.env.BASE_URL

export function asset(p: string): string {
  return BASE + p
}

const REPO = 'https://github.com/Qiuizi/yijing-workbench-public'

export const LINKS = {
  repo: REPO,
  releases: REPO + '/releases',
  releaseTag: REPO + '/releases/tag/v3.3.1',
  download: REPO + '/releases/download/v3.3.1/yijing-workbench-3.3.1-x64-setup.exe',
  checksums: REPO + '/releases/download/v3.3.1/SHA256SUMS.txt',
  provenance: REPO + '/releases/download/v3.3.1/PROVENANCE.md',
  license: REPO + '/blob/main/LICENSE',
  privacy: REPO + '/blob/main/PRIVACY.md',
  source: REPO + '/blob/main/backend/data/README.md',
  thirdParty: REPO + '/blob/main/THIRD_PARTY_NOTICES.txt',
  reviewPolicy: REPO + '/blob/main/docs/learning-approval-policy.md',
}

export const GITHUB_API = 'https://api.github.com/repos/Qiuizi/yijing-workbench-public/releases/latest'

// Pinned v3.3.1 facts used as the download-section fallback.
export const RELEASE_STATIC = {
  tag: 'v3.3.1',
  date: '2026-10-24',
  assetName: 'yijing-workbench-3.3.1-x64-setup.exe',
  bytes: 16097113,
  sha256: '3CAECBE2CE7684805BA5FBE2D8F60767101CCD71565A4EC37BACB2181B086B74',
}

export const APP_VERSION = 'v3.3.1'
