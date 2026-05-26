# Holdout Answer Protocol

This note records the Round-3 protocol fix for future blind source-holdout
answer agents.

When preparing `answer_for_review`, the answer must preserve concise source
anchors in the review-facing prose. Use source IDs plus a human locator and,
where relevant, a source-role qualifier.

Acceptable anchor shape:

`(SRC-W-TEC-04, ARF 6.6.5; SRC-W-TEC-30, TS05 WalletRelyingParty.usesIntermediary)`

Do include:

- source ID
- locator, section, article, page, or heading path
- source-role qualifier when the claim depends on legal/spec/project status

Do not include:

- repository names
- file paths
- artifact paths
- source anchors invented only for review

The goal is that reviewers can score traceability when the answer is
source-grounded, while redaction remains minimal because no local repository
paths are exposed.
