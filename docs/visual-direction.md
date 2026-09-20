# Visual Direction v0.2

## Core contrast

**Environment:** semi-realistic / realistic hotel  
**Characters:** stylized 3D  
**Lighting:** realistic cinematic  
**UI / PMS:** grounded corporate realism  
**Supernatural effects:** restrained

The visual identity should come from the contrast between a believable hotel and noticeably stylized people.

## Environment

The hotel should feel physically credible:
- realistic architectural proportions;
- believable hotel materials;
- real-world lighting logic;
- readable public vs BOH spaces;
- subtle wear and operational detail;
- no exaggerated cartoon geometry in the building itself.

The environment does not need absolute photorealism. It should be convincing enough that the player feels they are working in a real hotel.

## Characters

Characters should be clearly stylized rather than photorealistic.

Target:
- recognizable human anatomy;
- slightly exaggerated proportions;
- simplified facial construction;
- expressive eyes, brows, mouth and silhouettes;
- clean readable shapes;
- animation allowed to be a little broader than real life.

Avoid:
- chibi proportions;
- extreme caricature;
- rubber-hose animation;
- photorealistic MetaHuman look;
- characters that appear to come from a completely different lighting/rendering pipeline.

## Why this fits the game

The style supports both halves of the project:

### Workplace comedy
Stylized characters make reactions, guest complaints and coworker banter more readable and memorable.

### Drama
Characters can still carry serious scenes because proportions remain human and performances are grounded.

### Mystery
The realistic hotel keeps Room 713 and architectural inconsistencies believable. Stylized familiar coworkers placed in increasingly strange spaces can become subtly unsettling without changing the art style.

## Rendering rule

Environment and characters must share:
- the same scene lighting;
- the same shadow logic;
- the same reflection environment;
- compatible material response;
- consistent color grading.

The contrast comes from **shape language**, not from compositing two unrelated visual styles.

## Character material direction

Working idea:
- slightly simplified skin shader;
- controlled roughness;
- less pore-level detail;
- stylized hair masses instead of strand-heavy realism;
- simplified but physically plausible fabric;
- realistic cast shadows.

## Facial animation

Prioritize:
- strong poses;
- brows;
- eyes;
- head movement;
- mouth shapes;
- timing.

Do not make high-end facial capture a requirement for the vertical slice.

## Vertical slice rule

For Hotel Sandbox / Shift 1:
- greybox environment first;
- placeholder mannequin or simple stylized test character is acceptable;
- final character art is not a blocker for Interaction, PMS, radio or guest-flow systems.

The first polished character should be created only after the Hotel Sandbox loop works.

## Target feeling

The player should think:

> "This hotel could almost be real, but the people belong to a distinctive illustrated world."

The style should feel intentional, not like realistic assets mixed with cartoon models by accident.
