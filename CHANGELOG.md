All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Responsive dashboard on small screens with cards that regroup correctly.
- Minimalist redesign of the dashboard with Bootstrap Icons on each card.
- New document button adjusted to a less intrusive gray style.
- Dashboard counters restricted by role: only admins see global totals for users, categories, and tags.
- Non-admin users only see counts for records they have access to, preventing the disclosure of restricted information.
- Fixed document creation so the selected category is correctly persisted from the editor UI.
- Added category assignment validation in the backend to prevent assigning inaccessible or invalid categories.
- Category links in document view now point to filtered document lists, while list results remain ACL-filtered per user.
- Reserved category management to admins and enabled editors to view/create/edit/delete tags.
- Changed slug uniqueness for categories and tags to apply only to root-level nodes; child nodes can reuse slugs.
- Added defensive validation when moving a child category or tag to root if its slug conflicts with an existing root slug.
- Hardened transactional safety by wrapping commit/flush operations with rollback-on-error guards to prevent PendingRollback transaction poisoning.
- Added migration `20260426_02` to replace global slug uniqueness with root-scoped unique indexes for categories and tags.
- Added tests for editor tag permissions, root-scoped slug uniqueness, and category links in document views.


## [0.0.3] - 2026-04-25

### Changed

 - Refactor lateral navbar

## [0.0.2] - 2026-04-24

### Changed

 - Improved categories setup

## [0.0.1] - 2026-04-23

Initial release
