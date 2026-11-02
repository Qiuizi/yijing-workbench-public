// Single source of truth for URLs and pinned release facts (from PROVENANCE.md / project facts).
export const BASE = import.meta.env.BASE_URL

export function asset(p: string): string {
  return BASE + p
}

const REPO = 'https://github.com/Qiuizi/yijing-workbench-public'

export const LINKS = {
  repo: REPO,
  releases: REPO + '/releases',
  releaseTag: REPO + '/releases/tag/v3.3.2',
  download: REPO + '/releases/download/v3.3.2/yijing-workbench-3.3.2-x64-setup.exe',
  checksums: REPO + '/releases/download/v3.3.2/SHA256SUMS.txt',
  provenance: REPO + '/releases/download/v3.3.2/PROVENANCE.md',
  license: REPO + '/blob/main/LICENSE',
  privacy: REPO + '/blob/main/PRIVACY.md',
  source: REPO + '/blob/main/backend/data/README.md',
  thirdParty: REPO + '/blob/main/THIRD_PARTY_NOTICES.txt',
  reviewPolicy: REPO + '/blob/main/docs/learning-approval-policy.md',
}

export const GITHUB_API = 'https://api.github.com/repos/Qiuizi/yijing-workbench-public/releases/latest'

// Pinned v3.3.1 facts used as the download-section fallback.
export const RELEASE_STATIC = {
  tag: 'v3.3.2',
  date: '2026-11-02',
  assetName: 'yijing-workbench-3.3.2-x64-setup.exe',
  bytes: 13469345,
  sha256: 'BDA356AFE6FF63086DF1608110389067A70A051CDFA187F5CE23E655F273D999',
}

export const APP_VERSION = 'v3.3.2'
