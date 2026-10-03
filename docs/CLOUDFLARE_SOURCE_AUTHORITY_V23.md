# Cloudflare Production Source Authority v2.3

Status: **Phase 2C audit contract**

## Current production authority

Worker:

```text
apcs-rec-writeback
```

Production:

```text
Version #51
6c1e4f06-d7c5-4a33-91eb-9b788386a23d
deployment e7641e63-7d35-4468-8369-5072b94b15f2
traffic 100%
```

Existing clean-source receipt fingerprint:

```text
c4f2271c73a928a4dd757aaa160be303d3e555b0cfee80f156b2ca6956c7ba67
```

That historical fingerprint remains release evidence.  Do **not** compare it
to a different hashing algorithm and claim equality.

## Source-authority gap

The production Wrangler project is not currently versioned in
`brianlee-tw/APCS-Practice`.

Known canonical local project:

```text
C:\Users\ASUS\Documents\apcs-rec-writeback-cloudflare-v5-6-clean\apcs-rec-writeback-cloudflare-v5-5
```

Known project structure:

```text
src/index.ts
src/routing.ts
public/
wrangler.jsonc
package.json
```

Before any production slimming or refactor, re-capture that source and prove
which exact source tree is being reviewed.

## Read-only audit command

From the APCS-Practice repository in WSL:

```bash
python3 tools/cloudflare_source_audit.py \
  "/mnt/c/Users/ASUS/Documents/apcs-rec-writeback-cloudflare-v5-6-clean/apcs-rec-writeback-cloudflare-v5-5" \
  --json /tmp/apcs-worker-source-audit.json
```

The tool:

- never deploys;
- never performs network requests;
- excludes secret-bearing local files such as `.dev.vars` / `.env*`;
- excludes generated/dependency directories;
- reports only secret **names/references**, never secret values;
- inventories source/public bytes and route-like literals;
- fails if test-only production markers are still present;
- computes a versioned deterministic tree audit fingerprint.

The audit fingerprint is:

```text
cloudflare-source-audit-v1
sha256(relative_path\0decimal_size\0sha256(file_bytes)\n ...)
```

over sorted UTF-8 relative paths after exclusions.

## Phase 2C gate

Do not perform source slimming until all are true:

1. required Wrangler project files exist;
2. project name is `apcs-rec-writeback`;
3. compatibility date/flags match the production receipt;
4. source references only expected binding names;
5. no test-only route/secret marker remains;
6. route inventory preserves learner + Direct Write compatibility;
7. the exact audited source tree is placed under durable Git authority;
8. dry-run and existing production QA can be reproduced from that authority.

Until then, source slimming is **DEFERRED**, not failed.

No production redeploy is required merely to close source authority.
