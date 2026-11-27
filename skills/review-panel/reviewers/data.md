# Data

Review only what the change touches among: migrations, the event store and event schemas, projections built from events, and money or quantity maths.

Look for: a migration that loses or rewrites data or cannot run twice; an event shape change that breaks replay of events already stored; a projection that diverges from the events; rounding, overflow, unit or precision errors, float where an exact type is needed. Quote the line in `evidence` and give the stored value or sum that comes out wrong. `blocking` when stored data or money comes out wrong.

**Where events are the record** (event sourcing), apply the replay test to every event and command handler the change touches: if the business rule behind it were different tomorrow, would replaying the stored events give the new answer? A stored event cannot be changed, and neither can the absence of one. Two ways to fail the test, both `blocking`:

- an event that carries a conclusion (a status, an owner, a winner) instead of the act and the data the actor gave;
- a command handler that returns success yet records nothing, or records something other than what the caller did, because of the current state. "It changes nothing" is read from state that today's rule produced.

Not failures: a handler that refuses an invalid command (the caller is told, nothing happened), and one that leaves out the same command delivered twice. Input from outside (a file's rows, readings, prices) is not an event either: it is data the domain reads when it decides, kept in tables, and only what an actor or the domain did is recorded. A stream that grows with facts no longer needed to rebuild state is for compaction to shorten, not for the handler to thin out.
