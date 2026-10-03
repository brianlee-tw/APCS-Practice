# Cloudflare Worker operational source

This directory is the Git-controlled operational source for `apcs-rec-writeback`.

## Baseline

`src/index.mjs` is an exact byte-for-byte copy of production Worker version #51:

- version: `6c1e4f06-d7c5-4a33-91eb-9b788386a23d`
- deployment: `e7641e63-7d35-4468-8369-5072b94b15f2`
- SHA-256: `c4f2271c73a928a4dd757aaa160be303d3e555b0cfee80f156b2ca6956c7ba67`

The immutable recovery copy remains at `cloudflare/recovery/worker-51/index.mjs`.

Static assets are referenced from the immutable recovered tree at
`cloudflare/recovery/assets-51/public`.

## TypeScript status

The historical UI 5.17.0 TypeScript authoring project was recovered, but it predates the
v2.3 remote-writeback patch deployed on 2026-10-02. The exact original TypeScript used to
produce Worker #51 was not recovered.

For that reason, the exact production MJS is the current operational source authority.
A future TypeScript reconstruction must first demonstrate behavioral/bundle parity and
must not overwrite the immutable recovery evidence.

## Safety

Do not commit secrets. The production secret bindings remain Cloudflare-managed:
`NOTION_API_TOKEN` and `WRITE_KEY`.

Do not deploy directly from `main`. Use the existing safe-release process:
fresh candidate, preview QA, production-host 0% override QA, promotion, convergence,
full production QA, and rollback on any post-staging failure.
