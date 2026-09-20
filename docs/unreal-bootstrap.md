# Unreal Bootstrap

## Requirements

- Unreal Engine 5.8
- Git
- Git LFS

## First clone

```bash
git clone https://github.com/JohnCook36/wheres-my-room.git
cd wheres-my-room
git switch develop
git lfs install
git lfs pull
```

For work on the Unreal foundation branch:

```bash
git switch feature/unreal-project-foundation
```

## First open

Open:

`WheresMyRoom.uproject`

The project intentionally starts as a **Blueprint-only** project.

Do not add C++ until a real system benefits from it.

## First editor tasks

On the first successful editor launch:

1. create the Content folder hierarchy described in `Content/README.md`;
2. create a temporary prototype map;
3. save it as `Content/Maps/L_PrototypeEntry.umap`;
4. configure it as the Editor Startup Map and Game Default Map;
5. create the first-person player Blueprint;
6. create the common interaction interface;
7. verify that generated folders remain ignored by Git.

## First validation

Before committing Unreal-generated content:

```bash
git status --short
```

Expected generated directories such as `Saved/`, `Intermediate/`, `Binaries/`, and `DerivedDataCache/` must not appear as tracked files.

## Git LFS validation

After creating the first `.uasset` or `.umap`:

```bash
git lfs ls-files
```

The new Unreal binary assets must appear in the LFS list.
