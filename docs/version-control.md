# Version Control

## Repository

GitHub repository:

`JohnCook36/wheres-my-room`

## Git LFS

Binary Unreal and source-art files are tracked with Git LFS through `.gitattributes`.

Before the first Unreal asset commit on a development machine:

```bash
git lfs install
git lfs pull
```

## Branches

Initial lightweight workflow:

- `main` — stable baseline
- `develop` — active integration branch
- `feature/*` — individual features
- `fix/*` — bug fixes
- `docs/*` — larger documentation-only work when useful

Avoid a complex Git Flow until the project or team actually needs it.

## Commit examples

```text
chore: initialize unreal project foundation
feat(interaction): add first-person interaction trace
feat(pms): add reservation search prototype
feat(hotel): add lobby greybox
fix(elevator): prevent duplicate floor requests
docs: document room data model
```

## Unreal rules

Do not commit generated folders:

- `Binaries/`
- `DerivedDataCache/`
- `Intermediate/`
- `Saved/`

Do not work on the same `.umap` or major Blueprint simultaneously from different branches without coordination. Unreal assets are binary and Git cannot meaningfully merge most asset conflicts.
