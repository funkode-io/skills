# Data

Review only what the change touches among: migrations, the event store and event schemas, projections built from events, and money or quantity maths.

Look for: a migration that loses or rewrites data or cannot run twice; an event shape change that breaks replay of events already stored; a projection that diverges from the events; rounding, overflow, unit or precision errors, float where an exact type is needed. Quote the line in `evidence` and give the stored value or sum that comes out wrong. `blocking` when stored data or money comes out wrong.
