# Feature: Persistent library catalogue

Extend the existing Library module.

## Requirements

- Preserve the existing add_book behavior.
- Represent each book with title, author and read status.
- Support adding books.
- Support removing books by title.
- Support marking a book as read.
- Reject duplicate titles with a clear ValueError.
- Raise a clear error when a requested title does not exist.
- Save the catalogue to JSON.
- Load the catalogue from JSON.
- Add unit tests for every behavior.
- Use only the Python standard library.
- Do not modify unrelated files.
- Do not commit or push.

## Completion criteria

- All tests pass.
- Existing behavior remains supported.
- Every requirement has reviewer evidence.