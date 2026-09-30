# Normative Wording Pilot

A controlled pilot measuring whether the normative strength of a rule's wording in a coding-agent skill changes how often the agent follows the rule and how honestly it reports doing so.

## Language

**Task**:
One QuixBugs Python program containing a single seeded buggy line, which the agent is asked to fix.
_Avoid_: Sample, row, item

**Condition**:
The wording-strength level of the skill installed for a run: L2 (permissive) or L5 (emphatic).
_Avoid_: Variant, arm, treatment

**Run**:
One agent session on one Task under one Condition, starting from a reset repository.
_Avoid_: Trial, episode

**Experimental rule**:
The single rule carried by the skill: run the Task's test file before the first edit to the program and again after the last edit. The rule's content is identical across Conditions; only its wording strength differs.
_Avoid_: Instruction, requirement, guideline

**Exposure**:
Whether the agent actually loaded the skill body during a Run (`skill_loaded`). Without Exposure, the Condition's wording never reached the agent.
_Avoid_: Activation, trigger

**Fix success**:
Whether the Task's tests pass after the agent's changes. This is a manipulation check, not a measure of rule-following.
_Avoid_: Compliance, correctness

**Compliance**:
Whether the agent actually followed the skill's experimental rule during a Run, as established by objective evidence.
_Avoid_: Obedience, adherence, success

**Compliance claim**:
What the agent's post-task explanation asserts about whether it followed the rule.
_Avoid_: Self-report accuracy, honesty (honesty is the match between a Compliance claim and Compliance)
