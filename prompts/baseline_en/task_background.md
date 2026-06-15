### Task Background: Open Coding of Metaverse/VR Game Experience Value

You are assisting with the analysis of Chinese user reviews about immersive metaverse/VR game experience value.

#### Background

- Experience value refers to the benefits and value users perceive through actual interaction with a product, service, or environment.
- In traditional marketing research, experience value often includes service excellence, playfulness or entertainment, aesthetic value, and consumer return on investment.
- Immersive metaverse/VR games may include these related values, and may also present new dimensions related to virtual reality devices, immersive interaction, spatial environments, and service processes.

#### Analytical Tasks

- Identify how users describe value during the experience process.
- Extract text fragments directly related to experience value from a single review.
- Generate concise, reusable Chinese item labels for text fragments.
- Merge related item labels into higher-level dimensions with clear boundaries.
- Maintain a stable and extensible codebook that can absorb new evidence.

#### Judgment Rules

- A single user review is the primary text unit.
- Extract only fragments directly related to experience value.
- Item labels should stay close to empirical text while remaining reusable across reviews.
- Dimensions should summarize the shared meanings of multiple related items, not mechanically concatenate item names.
- When coding later samples, prioritize alignment with existing items and dimensions, and expand only when necessary.

#### Output Requirements

- Output structured JSON according to the specific task requirements.
- Labels, items, and dimension names should preferably use **concise Chinese**.
