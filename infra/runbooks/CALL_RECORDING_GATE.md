# Call recording and transcription gate

Audio intake, Asterisk ARI event handling, recording, transcription and retention are disabled in
the pilot until B02, B08 and B10 are resolved. Enabling any part of this path requires all of the
following evidence:

1. written legal basis, caller notice/consent rules, retention period and deletion owner;
2. approved Asterisk/ARI endpoint, authentication, network scope and authoritative call identifier;
3. an object-storage class with encryption, region, access logging and deletion enforcement;
4. a PII-safe event contract containing immutable audio-object references, never audio or transcript
   text in logs, metrics or traces;
5. asynchronous transcription with explicit language/model versions, failure state and manual intake
   fallback; and
6. access, deletion, outage, replay and restore tests signed by the security and legal owners.

The future adapter must remain a separate process behind the canonical intake contract. A call keeps
its source identifier and provenance; transcription is an immutable derived artifact and never
silently replaces the source recording. Loss of Asterisk, object storage, GPUs or transcription must
not block web/manual appeal registration.
