# Two type-9 admissions in the working raids — 30 September 2026

Physical lobby validation passed in test 9064. Battle validation remains pending.
Raw captures and station identifiers remain private.

Both complete working Eden controls (same-save and distinct-save) send these bodies on
`0x80:2`, in this order:

| Reliable sequence | First tuple field | Second tuple field | Embedded station |
| --- | --- | --- | --- |
| 1 | 0 | 0 | host |
| 2 | 0 | 1 | guest |

Both have lowest pending 1. Sequence 1 has initialized/start/end/application flags (15),
sequence 2 has start/end/application flags (7). The complete decoded bodies match
`build_accept(host_id, slot=0, code=0)` and `build_accept(guest_id, slot=0, code=1)`.

Synthetic physical test 6943 sends only sequence 1 with the guest ID and second field 0.
Earlier notes describing the second field as a universal success code, or summarizing the
reference as one guest acceptance, omitted this distinction. The exact meaning of that second
field is not yet established by receiver disassembly, but the working host/guest values are
unambiguous. This could explain crossed seat association; it is not a confirmed fix.

Added opt-in `--match-eden-raid-admission`. When the actual guest joins, it emits the two
reference bodies with current host/guest station IDs, preserved ordering, lowest pending and
initialized flags. It creates no extra PlayerInfo or synthetic trainer. The existing single
acceptance remains the default for baseline comparison and other game flows.

Two regression tests check the independent field values and byte-exact bodies against both
private working captures. Next live validation is lobby-only, preserving actual guest Session
PlayerInfo and the established opening settings, without the ineffective Net-property byte
experiment. Check default Corviknight and a switch to Iron Hands in Cyrus's own slot; no Ready.

## Physical result 9064

The user saw PR with Mew in slot 1, with an icon no longer copied from Cyrus. Cyrus entered
with the actual automatic Corviknight in slot 2. Changing to Iron Hands updated Cyrus's slot 2
and left PR with Mew. Authenticated selection messages independently confirm guest species
823 then 992, and host species 151. No Ready or battle was attempted.

This is the first synthetic-host validation of correct lobby trainer/Pokemon association,
not yet a battle success. The same admission mode must be preserved for the battle trial,
together with the independent LZ4 roster correction. Do not test host disconnect yet.

Private capture `lab/sv-raid-paired-admission-9064.jsonl`, SHA256
`A4B8EB4753C1ED8DF89A48D6A5F40366FA474CB67D9836C0E9BE0F6085F4A11E`.
