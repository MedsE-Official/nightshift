# Feature: Color Track Clips by Name

## Goal

Add a command that colors Arrangement clips based on their exact names.

## Mandatory requirements

- Preserve the existing delete command.
- Use the clicked clip only to locate its parent Track.
- Process every Arrangement clip on that track.
- Group clips by exact name.
- Clips with the same name receive the same color.
- Different name groups receive different colors where possible.
- Group all changes into one Ableton undo transaction.
- Relative TypeScript imports must include `.js`.
- Add unit tests.
- Do not commit or push.

## Completion criteria

- All automated tests pass.
- TypeScript compilation passes.
- Lint passes.
- No mandatory requirement is missing.
- No unrelated files are changed.
